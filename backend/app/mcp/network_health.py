"""
Network Health Analyzer — comprehensive metrics aggregation for the
autonomous incentive orchestration engine.

Collects real-time metrics including:
- Active/inactive contributors
- Dataset backlog and completion rates
- GPU compute shortage detection
- Retention and growth rates
- Validation failure rates
- Campaign performance
- Treasury status
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import IncentiveCampaign, CampaignLifecycle
from app.models.dataset import Dataset, UploadStatus
from app.models.device import Device, DeviceStatus
from app.models.event import Event
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.task_result import TaskResult
from app.models.treasury import TreasuryLedger
from app.models.user import User
from app.models.user_retention import UserRetentionState

logger = logging.getLogger(__name__)


class NetworkHealthAnalyzer:
    """Aggregates real-time network health metrics for AI decision making."""

    async def get_full_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """Collect all network health metrics in a single pass."""
        now = datetime.now(timezone.utc)

        # ── Contributor metrics ──
        total_users = (await db.execute(
            select(func.count(User.id))
        )).scalar() or 0

        active_cutoff = now - timedelta(hours=24)
        active_contributors = (await db.execute(
            select(func.count(User.id)).where(
                User.is_active == True,  # noqa: E712
                User.last_active_at > active_cutoff,
            )
        )).scalar() or 0

        inactive_cutoff_48h = now - timedelta(hours=48)
        inactive_contributors = (await db.execute(
            select(func.count(User.id)).where(
                User.is_active == True,  # noqa: E712
                User.last_active_at < inactive_cutoff_48h,
            )
        )).scalar() or 0

        inactive_cutoff_72h = now - timedelta(hours=72)
        deeply_inactive = (await db.execute(
            select(func.count(User.id)).where(
                User.is_active == True,  # noqa: E712
                User.last_active_at < inactive_cutoff_72h,
            )
        )).scalar() or 0

        # ── New contributors (last 7 days) ──
        week_ago = now - timedelta(days=7)
        new_contributors_7d = (await db.execute(
            select(func.count(User.id)).where(User.created_at > week_ago)
        )).scalar() or 0

        # ── Device metrics ──
        online_devices = (await db.execute(
            select(func.count(Device.id)).where(
                Device.status.in_([DeviceStatus.ONLINE, DeviceStatus.COMPUTING])
            )
        )).scalar() or 0

        computing_devices = (await db.execute(
            select(func.count(Device.id)).where(
                Device.status == DeviceStatus.COMPUTING
            )
        )).scalar() or 0

        total_devices = (await db.execute(
            select(func.count(Device.id))
        )).scalar() or 0

        # ── Job/Dataset metrics ──
        active_jobs = (await db.execute(
            select(func.count(Job.id)).where(Job.status == JobStatus.ACTIVE)
        )).scalar() or 0

        under_supplied_jobs_q = await db.execute(
            select(Job).where(
                Job.status == JobStatus.ACTIVE,
                Job.active_workers < Job.required_workers,
            )
        )
        under_supplied_jobs = list(under_supplied_jobs_q.scalars().all())

        # Stalled workloads: active jobs with 0 workers
        stalled_jobs = [j for j in under_supplied_jobs if j.active_workers == 0]

        dataset_backlog = (await db.execute(
            select(func.count(Dataset.id)).where(
                Dataset.upload_status == UploadStatus.READY
            )
        )).scalar() or 0

        # ── Task completion metrics ──
        completed_tasks_24h = (await db.execute(
            select(func.count(Task.id)).where(
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at > active_cutoff,
            )
        )).scalar() or 0

        failed_tasks_24h = (await db.execute(
            select(func.count(Task.id)).where(
                Task.status == TaskStatus.FAILED,
                Task.completed_at > active_cutoff,
            )
        )).scalar() or 0

        total_tasks_24h = completed_tasks_24h + failed_tasks_24h
        validation_failure_rate = (
            round(failed_tasks_24h / total_tasks_24h, 4)
            if total_tasks_24h > 0
            else 0.0
        )

        # ── Retention rate ──
        # Users active in last 7 days / total users
        active_7d = (await db.execute(
            select(func.count(User.id)).where(
                User.is_active == True,  # noqa: E712
                User.last_active_at > week_ago,
            )
        )).scalar() or 0
        retention_rate = round(active_7d / max(total_users, 1), 4)

        # ── Daily growth rate ──
        yesterday = now - timedelta(days=1)
        new_today = (await db.execute(
            select(func.count(User.id)).where(User.created_at > yesterday)
        )).scalar() or 0
        daily_growth_rate = round(new_today / max(total_users, 1), 4)

        # ── Churn risk ──
        high_churn_q = await db.execute(
            select(func.count(UserRetentionState.id)).where(
                UserRetentionState.churn_risk_score > 0.7
            )
        )
        high_churn_users = high_churn_q.scalar() or 0

        # ── Campaign metrics ──
        active_campaigns = (await db.execute(
            select(func.count(IncentiveCampaign.id)).where(
                IncentiveCampaign.status == "active"
            )
        )).scalar() or 0

        total_campaigns = (await db.execute(
            select(func.count(IncentiveCampaign.id))
        )).scalar() or 0

        # ── Treasury ──
        treasury_q = await db.execute(select(TreasuryLedger).limit(1))
        treasury = treasury_q.scalar_one_or_none()
        treasury_balance = treasury.available_balance if treasury else 100_000.0
        treasury_utilization = treasury.utilization_rate if treasury else 0.0

        # ── Avg reward multiplier ──
        avg_mult = (await db.execute(
            select(func.avg(Job.reward_multiplier)).where(
                Job.status == JobStatus.ACTIVE
            )
        )).scalar() or 1.0

        # ── Top contributor uptime (avg reliability) ──
        top_reliability = (await db.execute(
            select(func.avg(UserRetentionState.reliability_score))
        )).scalar() or 1.0

        # GPU compute shortage: more under-supplied than 40% of active jobs
        gpu_compute_shortage = (
            len(under_supplied_jobs) > max(active_jobs * 0.4, 1)
            if active_jobs > 0
            else False
        )

        # ── Referral events (last 7 days) ──
        referral_count = (await db.execute(
            select(func.count(Event.id)).where(
                Event.event_name == "referral_completed",
                Event.created_at > week_ago,
            )
        )).scalar() or 0

        return {
            # Core network metrics
            "active_contributors": active_contributors,
            "inactive_contributors": inactive_contributors,
            "deeply_inactive_contributors": deeply_inactive,
            "total_contributors": total_users,
            "new_contributors_7d": new_contributors_7d,
            "high_churn_users": high_churn_users,

            # Device/compute metrics
            "online_devices": online_devices,
            "computing_devices": computing_devices,
            "total_devices": total_devices,
            "gpu_compute_shortage": gpu_compute_shortage,

            # Workload metrics
            "active_jobs": active_jobs,
            "dataset_backlog": dataset_backlog,
            "under_supplied_count": len(under_supplied_jobs),
            "stalled_workloads": len(stalled_jobs),
            "under_supplied_jobs": [
                {
                    "job_id": str(j.id),
                    "name": j.name,
                    "active_workers": j.active_workers,
                    "required_workers": j.required_workers,
                    "priority": j.priority,
                    "reward_multiplier": j.reward_multiplier,
                }
                for j in under_supplied_jobs[:15]
            ],

            # Performance metrics
            "completed_tasks_24h": completed_tasks_24h,
            "failed_tasks_24h": failed_tasks_24h,
            "validation_failure_rate": validation_failure_rate,
            "avg_reward_multiplier": round(float(avg_mult), 2),

            # Retention/growth
            "retention_rate": retention_rate,
            "daily_growth_rate": daily_growth_rate,
            "top_contributor_reliability": round(float(top_reliability), 4),

            # Campaigns
            "active_campaigns": active_campaigns,
            "total_campaigns": total_campaigns,

            # Treasury
            "treasury_balance": treasury_balance,
            "treasury_utilization": treasury_utilization,

            # Referrals
            "referral_count_7d": referral_count,

            # Timestamp
            "snapshot_at": now.isoformat(),
        }


# Singleton
network_health = NetworkHealthAnalyzer()
