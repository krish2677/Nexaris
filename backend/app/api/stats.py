"""
Stats API — platform-wide statistics.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.device import Device, DeviceStatus
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.task_result import TaskResult
from app.models.user import User
from app.schemas.stats import PlatformStats
from app.websocket.hub import ws_manager

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/", response_model=PlatformStats)
async def platform_stats(db: AsyncSession = Depends(get_db)):
    """Get real-time platform statistics."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_devices = (
        await db.execute(
            select(func.count(Device.id)).where(
                Device.status.in_([DeviceStatus.ONLINE, DeviceStatus.COMPUTING])
            )
        )
    ).scalar() or 0
    total_jobs = (await db.execute(select(func.count(Job.id)))).scalar() or 0
    active_jobs = (
        await db.execute(
            select(func.count(Job.id)).where(Job.status == JobStatus.ACTIVE)
        )
    ).scalar() or 0
    completed_tasks = (
        await db.execute(
            select(func.count(Task.id)).where(Task.status == TaskStatus.COMPLETED)
        )
    ).scalar() or 0
    pending_tasks = (
        await db.execute(
            select(func.count(Task.id)).where(
                Task.status.in_([TaskStatus.PENDING, TaskStatus.QUEUED])
            )
        )
    ).scalar() or 0

    # Compute actual compute hours from execution_time_ms
    total_ms = (
        await db.execute(
            select(func.coalesce(func.sum(TaskResult.execution_time_ms), 0))
        )
    ).scalar() or 0
    total_compute_hours = round(total_ms / (1000 * 60 * 60), 2)

    # Average reward multiplier across active jobs
    avg_mult = (
        await db.execute(
            select(func.avg(Job.reward_multiplier)).where(
                Job.status == JobStatus.ACTIVE
            )
        )
    ).scalar() or 1.0

    return PlatformStats(
        total_users=total_users,
        active_devices=active_devices,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        total_compute_hours=total_compute_hours,
        avg_reward_multiplier=round(float(avg_mult), 2),
    )
