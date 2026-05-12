"""
Task service — distribution, locking, submission, stale recovery,
worker accounting, device ownership, validation trigger, and
event emission for MCP/Torque integration.

NOTE: The old aggregate_job_results() function has been removed.
All aggregation now goes through app.services.aggregation_service.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.device import Device, DeviceStatus
from app.models.event import Event
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.task_result import TaskResult, ValidationStatus
from app.schemas.task import TaskAssignment, TaskSubmission

logger = logging.getLogger(__name__)


async def verify_device_ownership(db: AsyncSession, device_id: UUID, user_id: UUID) -> Device:
    """Verify that the device belongs to the requesting user."""
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise ValueError("Device not found or does not belong to you")
    return device


async def assign_task(db: AsyncSession, device_id: UUID, user_id: UUID) -> TaskAssignment | None:
    """Find the highest-priority pending task, lock it, and assign to device.
    Validates device ownership before assignment."""
    # Verify device-user binding
    device = await verify_device_ownership(db, device_id, user_id)

    # Find a pending task from an active job, ordered by priority
    stmt = (
        select(Task)
        .join(Job, Task.job_id == Job.id)
        .where(
            Task.status == TaskStatus.PENDING,
            Job.status.in_([JobStatus.PENDING, JobStatus.ACTIVE]),
        )
        .order_by(Job.priority.desc(), Job.reward_multiplier.desc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        return None

    # Lock the task
    task.status = TaskStatus.IN_PROGRESS
    task.assigned_device_id = device_id
    task.locked_at = datetime.now(timezone.utc)

    # Update device status
    device.status = DeviceStatus.COMPUTING
    device.last_seen = datetime.now(timezone.utc)

    # Update job active worker count
    await db.execute(
        update(Job)
        .where(Job.id == task.job_id)
        .values(
            active_workers=Job.active_workers + 1,
            status=JobStatus.ACTIVE,
        )
    )

    await db.commit()
    await db.refresh(task)

    # Fetch the parent job for template info
    job_result = await db.execute(select(Job).where(Job.id == task.job_id))
    job = job_result.scalar_one()

    return TaskAssignment(
        id=task.id,
        job_id=task.job_id,
        template_type=job.template_type.value,
        parameters_json=job.parameters_json,
        range_start=task.range_start,
        range_end=task.range_end,
        chunk_reference=task.chunk_reference,
        reward_multiplier=job.reward_multiplier,
    )


async def submit_result(db: AsyncSession, submission: TaskSubmission, user_id: UUID) -> bool:
    """Store a task result with device verification, duplicate guard,
    execution time tracking, and automatic validation trigger."""
    # Verify device-user binding (with graceful fallback).
    # The JWT already authenticates the user. If the device was re-registered
    # under a different user (e.g., after re-login), we fall back to verifying
    # the device simply exists, rather than rejecting valid computation.
    try:
        device = await verify_device_ownership(db, submission.device_id, user_id)
    except ValueError:
        # Fallback: check if device exists at all (ownership mismatch)
        result = await db.execute(
            select(Device).where(Device.id == submission.device_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            raise ValueError("Device not found")
        logger.warning(
            f"Device ownership mismatch: device={submission.device_id} "
            f"(owner={device.user_id}) submitter={user_id}. "
            f"Accepting submission — JWT auth is the security layer."
        )

    # Verify task exists and can accept results.
    # Accept results for PENDING / IN_PROGRESS / VALIDATING tasks.
    # A task may have been re-queued (PENDING) by stale recovery while the
    # worker was still computing. We should still accept the result.
    result = await db.execute(select(Task).where(Task.id == submission.task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise ValueError("Task not found")

    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
        logger.debug(
            f"Rejecting duplicate submission for task {submission.task_id}: "
            f"status={task.status.value} (terminal state, worker will stop retrying)"
        )
        raise ValueError(f"Task already in terminal state: {task.status.value}")

    # Guard: reject duplicate result from the same device
    existing = await db.execute(
        select(TaskResult).where(
            TaskResult.task_id == submission.task_id,
            TaskResult.device_id == submission.device_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Duplicate result from same device")

    # Extract execution time from result if available
    result_data = json.loads(submission.result_json)
    exec_time = result_data.pop("execution_time_ms", None)

    # Store result
    task_result = TaskResult(
        task_id=submission.task_id,
        device_id=submission.device_id,
        result_json=json.dumps(result_data) if exec_time else submission.result_json,
        execution_time_ms=exec_time,
        validation_status=ValidationStatus.PENDING,
    )
    db.add(task_result)

    # Update device status and decrement active worker count
    await db.execute(
        update(Device)
        .where(Device.id == submission.device_id)
        .values(status=DeviceStatus.IDLE, last_seen=datetime.now(timezone.utc))
    )
    await db.execute(
        update(Job)
        .where(Job.id == task.job_id, Job.active_workers > 0)
        .values(active_workers=Job.active_workers - 1)
    )

    # Flush to ensure the new TaskResult is in the DB before counting
    await db.flush()

    # Check if we have enough results for validation
    # NOTE: Do NOT add +1 here — flush() above already made the row visible.
    # The old +1 caused an off-by-one with autoflush=True (default),
    # which triggered VALIDATING after only 1 result, causing tasks to
    # get stuck forever.
    result_count_q = await db.execute(
        select(func.count(TaskResult.id)).where(
            TaskResult.task_id == submission.task_id
        )
    )
    result_count = result_count_q.scalar() or 0

    if result_count >= settings.VALIDATION_DUPLICATE_COUNT:
        task.status = TaskStatus.VALIDATING
    else:
        # Re-queue for duplicate validation — needs another device
        task.status = TaskStatus.PENDING
        task.assigned_device_id = None
        task.locked_at = None

    await db.commit()

    # ── Trigger validation if enough results ──
    if result_count >= settings.VALIDATION_DUPLICATE_COUNT:
        try:
            from app.services.validation_service import validate_task
            is_valid = await validate_task(db, submission.task_id)

            if is_valid:
                # ── Emit validated_work_unit_completed event for MCP scoring ──
                job_q = await db.execute(select(Job).where(Job.id == task.job_id))
                job = job_q.scalar_one()

                event = Event(
                    user_id=user_id,
                    event_name="validated_work_unit_completed",
                    job_id=task.job_id,
                    device_id=submission.device_id,
                    metadata_json=json.dumps({
                        "task_id": str(submission.task_id),
                        "device_power_factor": device.device_power_factor,
                        "urgency_multiplier": job.reward_multiplier,
                        "template_type": job.template_type.value,
                        "execution_time_ms": exec_time,
                    }),
                )
                db.add(event)

                # Update user last active
                from app.models.user import User
                await db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(last_active_at=datetime.now(timezone.utc))
                )

                await db.commit()

                # Broadcast via WebSocket
                try:
                    from app.websocket.hub import ws_manager
                    await ws_manager.broadcast("global", {
                        "type": "task_validated",
                        "task_id": str(submission.task_id),
                        "job_id": str(task.job_id),
                        "user_id": str(user_id),
                    })
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Validation trigger error for task {submission.task_id}: {e}")

    return True


async def recover_stale_tasks(db: AsyncSession) -> int:
    """Re-queue tasks that have been locked too long (worker disappeared).
    Also decrements active_worker count for affected jobs."""
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=settings.TASK_LOCK_TIMEOUT_SECONDS
    )
    # Find stale tasks first to get job IDs
    stale_q = await db.execute(
        select(Task).where(
            and_(
                Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.VALIDATING]),
                Task.locked_at < cutoff,
                Task.retry_count < settings.MAX_TASK_RETRIES,
            )
        )
    )
    stale_tasks = list(stale_q.scalars().all())

    for task in stale_tasks:
        task.status = TaskStatus.PENDING
        task.assigned_device_id = None
        task.locked_at = None
        task.retry_count += 1
        # Decrement active workers
        await db.execute(
            update(Job)
            .where(Job.id == task.job_id, Job.active_workers > 0)
            .values(active_workers=Job.active_workers - 1)
        )

    if stale_tasks:
        await db.commit()
        logger.info(f"Recovered {len(stale_tasks)} stale tasks")

    # Also handle exhausted tasks
    await fail_exhausted_tasks(db)

    return len(stale_tasks)


async def reset_failed_tasks(db: AsyncSession) -> int:
    """Reset FAILED tasks back to PENDING so they can be retried.
    This recovers tasks that were unfairly failed due to the 403 bug
    (device ownership mismatch, replay protection, etc.)."""
    stmt = (
        update(Task)
        .where(
            and_(
                Task.status == TaskStatus.FAILED,
                Task.retry_count <= settings.MAX_TASK_RETRIES + 2,  # Don't retry truly exhausted ones
            )
        )
        .values(
            status=TaskStatus.PENDING,
            retry_count=0,
            assigned_device_id=None,
            locked_at=None,
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    count = result.rowcount  # type: ignore[attr-defined]
    if count:
        logger.info(f"Reset {count} failed tasks back to PENDING for retry")
    return count


async def fail_exhausted_tasks(db: AsyncSession) -> int:
    """Mark tasks that exceeded max retries as failed."""
    stmt = (
        update(Task)
        .where(
            and_(
                Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.PENDING]),
                Task.retry_count >= settings.MAX_TASK_RETRIES,
            )
        )
        .values(status=TaskStatus.FAILED)
    )
    result = await db.execute(stmt)
    await db.commit()
    count = result.rowcount  # type: ignore[attr-defined]
    if count:
        logger.info(f"Failed {count} exhausted tasks (max retries reached)")
    return count
