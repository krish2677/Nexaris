"""
Jobs API — create, list, track computational jobs, and retrieve results.
Enforces ownership access control.
"""

from __future__ import annotations

import json
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse
from app.services.job_service import create_job, get_job_progress, get_jobs
from app.services.aggregation_service import aggregate_job, get_aggregation
from app.websocket.hub import ws_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create(
    data: JobCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new computational job with auto-partitioned tasks."""
    try:
        job = await create_job(db, user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Emit event for MCP and dashboard
    from app.models.event import Event
    event = Event(
        user_id=user.id,
        event_name="researcher_created_job",
        job_id=job.id,
        metadata_json=json.dumps({
            "job_name": job.name,
            "template_type": job.template_type.value,
            "required_workers": job.required_workers,
        }),
    )
    db.add(event)
    await db.commit()

    await ws_manager.broadcast("global", {
        "type": "job_created",
        "job_id": str(job.id),
        "name": job.name,
        "template_type": job.template_type.value,
    })

    return job


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    mine: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List jobs. Pass ?mine=true to see only your own jobs."""
    owner_id = user.id if mine else None
    jobs = await get_jobs(db, owner_id=owner_id)
    return jobs


@router.get("/{job_id}/progress")
async def job_progress(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get task completion progress for a job. Owner-only."""
    jid = UUID(job_id)
    # Verify ownership
    job_q = await db.execute(select(Job).where(Job.id == jid))
    job = job_q.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your job")

    progress = await get_job_progress(db, jid)

    # Add aggregation status if available
    agg = await get_aggregation(db, jid)
    if agg:
        progress["aggregation_status"] = agg.get("aggregation_status", "none")
        progress["aggregation_version"] = agg.get("aggregation_version", 0)

    return progress


@router.get("/{job_id}/results")
async def job_results(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated results for a job. Uses persisted aggregation.
    Owner-only."""
    jid = UUID(job_id)
    job_q = await db.execute(select(Job).where(Job.id == jid))
    job = job_q.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your job")

    # Try persisted aggregation first
    agg = await get_aggregation(db, jid)
    if agg:
        return agg

    # Compute fresh aggregation
    metrics = await aggregate_job(db, jid)
    return {
        "job_id": str(jid),
        "metrics": metrics,
        "aggregation_status": "computed",
    }
