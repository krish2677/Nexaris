"""
Research API — aggregated results, reports, downloads, and MCP status.
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.job import Job
from app.models.mcp_action import MCPAction, RewardCampaign, CampaignStatus
from app.models.user import User
from app.services.aggregation_service import aggregate_job, get_aggregation
from app.services.output_service import generate_report, generate_export

router = APIRouter(prefix="/jobs", tags=["research"])


@router.get("/{job_id}/aggregates")
async def job_aggregates(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the persisted aggregated results for a job."""
    jid = UUID(job_id)
    job_q = await db.execute(select(Job).where(Job.id == jid))
    job = job_q.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your job")

    # Try stored aggregation first
    agg = await get_aggregation(db, jid)
    if not agg:
        # Compute fresh aggregation
        metrics = await aggregate_job(db, jid)
        agg = await get_aggregation(db, jid)
        if not agg:
            return {"status": "no_results", "metrics": metrics}

    return agg


@router.get("/{job_id}/reports")
async def job_report(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return a research report for a job."""
    jid = UUID(job_id)
    job_q = await db.execute(select(Job).where(Job.id == jid))
    job = job_q.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your job")

    try:
        report = await generate_report(db, jid)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/{job_id}/download")
async def job_download(
    job_id: str,
    format: str = "json",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download job results as JSON, CSV, or ZIP archive."""
    jid = UUID(job_id)
    job_q = await db.execute(select(Job).where(Job.id == jid))
    job = job_q.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your job")

    if format not in ("json", "csv", "zip"):
        raise HTTPException(status_code=400, detail="Format must be json, csv, or zip")

    try:
        data, content_type, filename = await generate_export(db, jid, format)
        return Response(
            content=data,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(data)),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# ── MCP Status API ──

mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])


@mcp_router.get("/status")
async def mcp_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get MCP engine status, recent actions, and active campaigns."""
    from app.models.device import Device, DeviceStatus
    from app.models.job import JobStatus

    # Active workers
    active_q = await db.execute(
        select(func.count(Device.id)).where(
            Device.status.in_([DeviceStatus.ONLINE, DeviceStatus.COMPUTING])
        )
    )
    active_workers = active_q.scalar() or 0

    # Under-supplied jobs
    under_q = await db.execute(
        select(func.count(Job.id)).where(
            Job.status == JobStatus.ACTIVE,
            Job.active_workers < Job.required_workers,
        )
    )
    under_supplied = under_q.scalar() or 0

    # Active campaigns
    campaign_q = await db.execute(
        select(func.count(RewardCampaign.id)).where(
            RewardCampaign.status == CampaignStatus.ACTIVE
        )
    )
    active_campaigns = campaign_q.scalar() or 0

    # Recent actions (last 20)
    actions_q = await db.execute(
        select(MCPAction).order_by(MCPAction.created_at.desc()).limit(20)
    )
    recent_actions = [
        {
            "id": str(a.id),
            "action_type": a.action_type,
            "target_job_id": str(a.target_job_id) if a.target_job_id else None,
            "target_user_id": str(a.target_user_id) if a.target_user_id else None,
            "parameters": json.loads(a.parameters_json),
            "status": a.status.value if hasattr(a.status, 'value') else a.status,
            "source": a.source,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in actions_q.scalars().all()
    ]

    # Total MCP actions
    total_q = await db.execute(select(func.count(MCPAction.id)))
    total_actions = total_q.scalar() or 0

    # Average multiplier
    avg_q = await db.execute(
        select(func.avg(Job.reward_multiplier)).where(
            Job.status == JobStatus.ACTIVE
        )
    )
    avg_mult = avg_q.scalar() or 1.0

    return {
        "active_workers": active_workers,
        "under_supplied_jobs": under_supplied,
        "active_campaigns": active_campaigns,
        "recent_actions": recent_actions,
        "avg_multiplier": round(float(avg_mult), 2),
        "total_mcp_actions": total_actions,
    }


@mcp_router.get("/campaigns")
async def list_campaigns(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all reward campaigns."""
    result = await db.execute(
        select(RewardCampaign).order_by(RewardCampaign.start_time.desc()).limit(50)
    )
    campaigns = result.scalars().all()
    return {
        "campaigns": [
            {
                "id": str(c.id),
                "campaign_type": c.campaign_type,
                "multiplier": c.multiplier,
                "target_job_id": str(c.target_job_id) if c.target_job_id else None,
                "status": c.status.value if hasattr(c.status, 'value') else c.status,
                "start_time": c.start_time.isoformat() if c.start_time else None,
                "end_time": c.end_time.isoformat() if c.end_time else None,
            }
            for c in campaigns
        ]
    }
