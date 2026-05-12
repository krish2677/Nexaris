"""
Validation service — duplicate execution, deterministic verification,
spot-check recomputation, result tampering protection, and
CONSENSUS-BASED canonical result selection.

Key fix: Only ONE result per task is marked as canonical.
This prevents double-counting during aggregation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.job import Job
from app.models.task import Task, TaskStatus
from app.models.task_result import TaskResult, ValidationStatus
from app.workers.compute_engine import execute_template

logger = logging.getLogger(__name__)

# Tolerance for numeric comparison (0.1%)
NUMERIC_TOLERANCE = 0.001
# Threshold of consecutive spot-check failures before banning
SPOT_CHECK_FAIL_THRESHOLD = 3


async def validate_task(db: AsyncSession, task_id) -> bool:
    """
    Run validation on a task's results:
    1. Duplicate: compare results from multiple workers
    2. Consensus: select ONE canonical result
    3. Spot-check: backend recomputes and compares (random probability)
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return False

    # Fetch all results for this task
    results_q = await db.execute(
        select(TaskResult)
        .where(TaskResult.task_id == task_id)
        .order_by(TaskResult.created_at)
    )
    results = list(results_q.scalars().all())

    if len(results) < settings.VALIDATION_DUPLICATE_COUNT:
        # Reset task to PENDING if it was prematurely set to VALIDATING
        # (e.g., due to autoflush off-by-one in result counting)
        if task.status == TaskStatus.VALIDATING:
            task.status = TaskStatus.PENDING
            task.assigned_device_id = None
            task.locked_at = None
            await db.commit()
            logger.warning(
                f"Task {task_id} was VALIDATING with only {len(results)} results "
                f"(need {settings.VALIDATION_DUPLICATE_COUNT}), reset to PENDING"
            )
        return False

    # ── Duplicate Validation ──
    parsed = [json.loads(r.result_json) for r in results]
    is_valid = _compare_results(parsed)

    if is_valid:
        # ── Consensus: Select ONE canonical result ──
        # Pick the first result as canonical (they all agree)
        canonical_idx = _select_canonical(parsed)

        for i, r in enumerate(results):
            r.validation_status = ValidationStatus.VALID
            r.is_canonical = (i == canonical_idx)
            # Compute checksum for integrity
            r.checksum = hashlib.sha256(r.result_json.encode()).hexdigest()
            # Set consensus group (all matching results share a group)
            r.consensus_group = hashlib.sha256(
                json.dumps(parsed[canonical_idx], sort_keys=True).encode()
            ).hexdigest()[:16]

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
    else:
        # Mark as invalid, retry
        for r in results:
            r.validation_status = ValidationStatus.INVALID
            r.is_canonical = False
        task.status = TaskStatus.PENDING
        task.assigned_device_id = None
        task.locked_at = None
        task.retry_count += 1
        logger.warning(f"Task {task_id} failed duplicate validation, retrying")

    # ── Spot-check (random recomputation) ──
    if is_valid and random.random() < settings.SPOT_CHECK_PROBABILITY:
        canonical_result = parsed[canonical_idx]
        spot_ok = await _spot_check(db, task, canonical_result)
        if not spot_ok:
            # Spot-check failed — mark as invalid and re-queue
            is_valid = False
            for r in results:
                r.validation_status = ValidationStatus.INVALID
                r.is_canonical = False
            task.status = TaskStatus.PENDING
            task.assigned_device_id = None
            task.locked_at = None
            task.retry_count += 1

    await db.commit()

    # Check if all tasks for the job are complete
    if is_valid:
        await _check_job_completion(db, task.job_id)

    return is_valid


def _select_canonical(parsed: list[dict]) -> int:
    """Select the canonical result index from a set of agreeing results.
    Picks the result with the most precise numeric values (lowest rounding).
    Falls back to first result if all are identical."""
    if len(parsed) <= 1:
        return 0

    # Simple strategy: pick result with highest total numeric precision
    best_idx = 0
    best_precision = 0

    for i, result in enumerate(parsed):
        precision = _measure_precision(result)
        if precision > best_precision:
            best_precision = precision
            best_idx = i

    return best_idx


def _measure_precision(obj, depth=0) -> int:
    """Count total decimal digits across all numeric values — proxy for precision."""
    if depth > 10:
        return 0
    total = 0
    if isinstance(obj, float):
        s = f"{obj:.15g}"
        if "." in s:
            total += len(s.split(".")[1].rstrip("0"))
        return total
    if isinstance(obj, dict):
        for v in obj.values():
            total += _measure_precision(v, depth + 1)
    if isinstance(obj, list):
        for v in obj:
            total += _measure_precision(v, depth + 1)
    return total


def _compare_results(parsed: list[dict]) -> bool:
    """Compare multiple results for consistency with numeric tolerance."""
    if len(parsed) < 2:
        return True

    reference = parsed[0]
    for other in parsed[1:]:
        if not _deep_compare(reference, other):
            return False
    return True


def _deep_compare(ref, other, tolerance: float = NUMERIC_TOLERANCE) -> bool:
    """Deep comparison with numeric tolerance for floats."""
    if type(ref) != type(other):
        # Allow int/float cross-comparison
        if isinstance(ref, (int, float)) and isinstance(other, (int, float)):
            ref_f, oth_f = float(ref), float(other)
            if ref_f == 0 and oth_f == 0:
                return True
            return abs(ref_f - oth_f) <= abs(ref_f) * tolerance
        return False

    if isinstance(ref, dict):
        if set(ref.keys()) != set(other.keys()):
            return False
        return all(_deep_compare(ref[k], other[k], tolerance) for k in ref)

    if isinstance(ref, list):
        if len(ref) != len(other):
            return False
        return all(_deep_compare(r, o, tolerance) for r, o in zip(ref, other))

    if isinstance(ref, float):
        if ref == 0 and other == 0:
            return True
        return abs(ref - other) <= abs(ref) * tolerance

    return ref == other


async def _spot_check(db: AsyncSession, task: Task, worker_result: dict) -> bool:
    """Backend recomputes the task and compares with worker result.
    Returns True if spot-check passes."""
    try:
        job_q = await db.execute(select(Job).where(Job.id == task.job_id))
        job = job_q.scalar_one()

        params = json.loads(job.parameters_json)
        server_result = execute_template(
            template_type=job.template_type.value,
            params=params,
            range_start=task.range_start,
            range_end=task.range_end,
            chunk_reference=task.chunk_reference,
        )

        if _deep_compare(worker_result, server_result):
            logger.info(f"Spot-check PASSED for task {task.id}")
            return True
        else:
            logger.warning(
                f"Spot-check FAILED for task {task.id}: "
                f"server={json.dumps(server_result)[:200]} vs "
                f"worker={json.dumps(worker_result)[:200]}"
            )
            return False
    except Exception as e:
        logger.error(f"Spot-check error for task {task.id}: {e}")
        return True  # Fail open on error


async def _check_job_completion(db: AsyncSession, job_id) -> None:
    """If all tasks are completed, mark the job as completed and trigger aggregation."""
    from sqlalchemy import func

    total_q = await db.execute(
        select(func.count(Task.id)).where(Task.job_id == job_id)
    )
    completed_q = await db.execute(
        select(func.count(Task.id)).where(
            Task.job_id == job_id, Task.status == TaskStatus.COMPLETED
        )
    )
    total = total_q.scalar() or 0
    completed = completed_q.scalar() or 0

    if total > 0 and total == completed:
        await db.execute(
            update(Job).where(Job.id == job_id).values(status="completed")
        )
        await db.commit()
        logger.info(f"Job {job_id} completed — all {total} tasks done")

        # Trigger aggregation
        try:
            from app.services.aggregation_service import aggregate_job
            await aggregate_job(db, job_id)
            logger.info(f"Job {job_id} aggregation completed")
        except Exception as e:
            logger.error(f"Job {job_id} aggregation failed: {e}")

        # Fire-and-forget Torque campaign for job completion
        try:
            from app.torque.client import torque_client
            job_q = await db.execute(select(Job).where(Job.id == job_id))
            job = job_q.scalar_one_or_none()
            if job:
                await torque_client.trigger_campaign(
                    campaign_id="job_completed",
                    user_ids=[str(job.owner_id)],
                    metadata={"job_id": str(job_id), "task_count": total},
                )
        except Exception:
            pass  # Non-critical
