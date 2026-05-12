"""
MCP API — REST endpoints for the autonomous incentive orchestration engine.
Provides network health, treasury, campaigns, and agent decision log.
"""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.campaign import IncentiveCampaign, CampaignLifecycle, CampaignType
from app.models.device import Device, DeviceStatus
from app.models.job import Job, JobStatus
from app.models.mcp_action import MCPAction, RewardCampaign, CampaignStatus
from app.models.treasury import TreasuryLedger, TreasuryTransaction
from app.models.user import User
from app.models.user_retention import UserRetentionState
from app.mcp.budget_engine import budget_engine
from app.mcp.engine import mcp_engine
from app.mcp.network_health import network_health

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/status")
async def mcp_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get MCP engine status, recent actions, and live metrics."""
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

    # Active campaigns (both old and new models)
    old_campaigns = (await db.execute(
        select(func.count(RewardCampaign.id)).where(
            RewardCampaign.status == CampaignStatus.ACTIVE
        )
    )).scalar() or 0

    new_campaigns = (await db.execute(
        select(func.count(IncentiveCampaign.id)).where(
            IncentiveCampaign.status == "active"
        )
    )).scalar() or 0

    # Recent actions (last 30)
    actions_q = await db.execute(
        select(MCPAction).order_by(MCPAction.created_at.desc()).limit(30)
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
    total_actions = (await db.execute(select(func.count(MCPAction.id)))).scalar() or 0

    # Average multiplier
    avg_mult = (await db.execute(
        select(func.avg(Job.reward_multiplier)).where(Job.status == JobStatus.ACTIVE)
    )).scalar() or 1.0

    # High churn users
    high_churn = (await db.execute(
        select(func.count(UserRetentionState.id)).where(
            UserRetentionState.churn_risk_score > 0.7
        )
    )).scalar() or 0

    return {
        "engine_cycle": mcp_engine.cycle_count,
        "active_workers": active_workers,
        "under_supplied_jobs": under_supplied,
        "active_campaigns": old_campaigns + new_campaigns,
        "recent_actions": recent_actions,
        "avg_multiplier": round(float(avg_mult), 2),
        "total_mcp_actions": total_actions,
        "high_churn_users": high_churn,
    }


@router.get("/health")
async def network_health_metrics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive network health metrics."""
    metrics = await network_health.get_full_metrics(db)
    return metrics


@router.get("/treasury")
async def treasury_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get treasury budget allocation summary."""
    summary = await budget_engine.get_budget_summary(db)

    # Recent transactions
    txn_q = await db.execute(
        select(TreasuryTransaction).order_by(
            TreasuryTransaction.created_at.desc()
        ).limit(20)
    )
    transactions = [
        {
            "id": str(t.id),
            "campaign_id": str(t.campaign_id) if t.campaign_id else None,
            "category": t.category,
            "amount": t.amount,
            "description": t.description,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txn_q.scalars().all()
    ]

    summary["recent_transactions"] = transactions
    return summary


@router.get("/campaigns")
async def list_campaigns(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all incentive campaigns with full details."""
    # New campaigns
    result = await db.execute(
        select(IncentiveCampaign).order_by(
            IncentiveCampaign.created_at.desc()
        ).limit(50)
    )
    campaigns = result.scalars().all()

    return {
        "campaigns": [
            {
                "id": str(c.id),
                "name": c.name,
                "campaign_type": c.campaign_type,
                "priority": c.priority,
                "status": c.status,
                "reasoning": c.reasoning,
                "target_audience": c.target_audience,
                "reward_pool": c.reward_pool,
                "spent": c.spent,
                "multiplier": c.multiplier,
                "duration_hours": c.duration_hours,
                "torque_primitives": json.loads(c.torque_primitives_json or "[]"),
                "eligibility_rules": json.loads(c.eligibility_rules_json or "[]"),
                "success_metrics": json.loads(c.success_metrics_json or "[]"),
                "performance": json.loads(c.performance_json or "{}"),
                "source": c.source,
                "start_time": c.start_time.isoformat() if c.start_time else None,
                "end_time": c.end_time.isoformat() if c.end_time else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in campaigns
        ],
        "total": len(campaigns),
    }


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed campaign information."""
    cid = UUID(campaign_id)
    q = await db.execute(select(IncentiveCampaign).where(IncentiveCampaign.id == cid))
    campaign = q.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "campaign_type": campaign.campaign_type,
        "priority": campaign.priority,
        "status": campaign.status,
        "reasoning": campaign.reasoning,
        "target_audience": campaign.target_audience,
        "reward_pool": campaign.reward_pool,
        "spent": campaign.spent,
        "multiplier": campaign.multiplier,
        "duration_hours": campaign.duration_hours,
        "torque_primitives": json.loads(campaign.torque_primitives_json or "[]"),
        "eligibility_rules": json.loads(campaign.eligibility_rules_json or "[]"),
        "success_metrics": json.loads(campaign.success_metrics_json or "[]"),
        "performance": json.loads(campaign.performance_json or "{}"),
        "source": campaign.source,
        "start_time": campaign.start_time.isoformat() if campaign.start_time else None,
        "end_time": campaign.end_time.isoformat() if campaign.end_time else None,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
    }


@router.get("/retention")
async def retention_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get contributor retention overview."""
    states_q = await db.execute(
        select(UserRetentionState).order_by(
            UserRetentionState.churn_risk_score.desc()
        ).limit(50)
    )
    states = states_q.scalars().all()

    # Aggregate stats
    total = len(states)
    high_risk = sum(1 for s in states if s.churn_risk_score > 0.7)
    medium_risk = sum(1 for s in states if 0.3 < s.churn_risk_score <= 0.7)
    low_risk = sum(1 for s in states if s.churn_risk_score <= 0.3)
    avg_streak = sum(s.streak_days for s in states) / max(total, 1)
    avg_reliability = sum(s.reliability_score for s in states) / max(total, 1)

    return {
        "total_tracked": total,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
        "avg_streak_days": round(avg_streak, 1),
        "avg_reliability": round(avg_reliability, 3),
        "contributors": [
            {
                "user_id": str(s.user_id),
                "streak_days": s.streak_days,
                "churn_risk": round(s.churn_risk_score, 3),
                "reliability": round(s.reliability_score, 3),
                "total_validated": s.total_validated_tasks,
                "last_compute": s.last_compute_at.isoformat() if s.last_compute_at else None,
            }
            for s in states[:20]
        ],
    }
