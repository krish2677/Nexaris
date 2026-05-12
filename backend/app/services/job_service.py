"""
Job service — create jobs and generate work unit tasks.
"""

from __future__ import annotations

import json
import logging
from typing import List
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus, TemplateType, ValidationStrategy
from app.models.task import Task, TaskStatus
from app.schemas.job import JobCreate, JobResponse

logger = logging.getLogger(__name__)

# Default chunk sizes for each template type
CHUNK_SIZES = {
    TemplateType.MONTE_CARLO: 100_000,
    TemplateType.DATASET_STATS: 10_000,
    TemplateType.MATRIX_COMPUTE: 256,
}


async def create_job(db: AsyncSession, owner_id: UUID, data: JobCreate) -> Job:
    """Create a job and partition it into tasks."""
    template = TemplateType(data.template_type)
    strategy = ValidationStrategy(data.validation_strategy)
    params = json.loads(data.parameters_json)

    job = Job(
        owner_id=owner_id,
        name=data.name,
        template_type=template,
        parameters_json=data.parameters_json,
        priority=data.priority,
        required_workers=data.required_workers,
        validation_strategy=strategy,
    )
    db.add(job)
    await db.flush()

    # Generate tasks based on template type
    tasks = _partition_job(job, params)
    for t in tasks:
        t.job_id = job.id
        db.add(t)

    job.status = JobStatus.PENDING
    await db.commit()
    await db.refresh(job)
    logger.info(f"Created job {job.id} with {len(tasks)} tasks")
    return job


def _partition_job(job: Job, params: dict) -> List[Task]:
    """Split a job into independent work unit tasks."""
    tasks: List[Task] = []

    if job.template_type == TemplateType.MONTE_CARLO:
        total_iterations = params.get("total_iterations", 1_000_000)
        chunk = CHUNK_SIZES[TemplateType.MONTE_CARLO]
        for start in range(0, total_iterations, chunk):
            end = min(start + chunk, total_iterations)
            tasks.append(
                Task(range_start=start, range_end=end, status=TaskStatus.PENDING)
            )

    elif job.template_type == TemplateType.DATASET_STATS:
        total_rows = params.get("total_rows", 100_000)
        chunk = CHUNK_SIZES[TemplateType.DATASET_STATS]
        for start in range(0, total_rows, chunk):
            end = min(start + chunk, total_rows)
            tasks.append(
                Task(
                    range_start=start,
                    range_end=end,
                    chunk_reference=params.get("dataset_ref", ""),
                    status=TaskStatus.PENDING,
                )
            )

    elif job.template_type == TemplateType.MATRIX_COMPUTE:
        matrix_size = params.get("matrix_size", 1024)
        chunk = CHUNK_SIZES[TemplateType.MATRIX_COMPUTE]
        for row_start in range(0, matrix_size, chunk):
            row_end = min(row_start + chunk, matrix_size)
            tasks.append(
                Task(
                    range_start=row_start,
                    range_end=row_end,
                    chunk_reference=json.dumps(
                        {"matrix_size": matrix_size, "cols": [0, matrix_size]}
                    ),
                    status=TaskStatus.PENDING,
                )
            )

    return tasks


async def get_jobs(db: AsyncSession, owner_id: UUID | None = None) -> List[Job]:
    """List jobs, optionally filtered by owner."""
    stmt = select(Job).order_by(Job.created_at.desc())
    if owner_id:
        stmt = stmt.where(Job.owner_id == owner_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_job_progress(db: AsyncSession, job_id: UUID) -> dict:
    """Get task completion statistics for a job."""
    total_q = await db.execute(
        select(func.count(Task.id)).where(Task.job_id == job_id)
    )
    completed_q = await db.execute(
        select(func.count(Task.id)).where(
            Task.job_id == job_id, Task.status == TaskStatus.COMPLETED
        )
    )
    failed_q = await db.execute(
        select(func.count(Task.id)).where(
            Task.job_id == job_id, Task.status == TaskStatus.FAILED
        )
    )
    return {
        "total": total_q.scalar() or 0,
        "completed": completed_q.scalar() or 0,
        "failed": failed_q.scalar() or 0,
    }
