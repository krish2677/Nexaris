"""
Task API — fetch tasks and submit results.
Enforces device-user binding and secure event emission.

NOTE: Validation and event emission are now handled inside
      task_service.submit_result() to prevent double-validation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.event import Event
from app.models.user import User
from app.schemas.task import TaskAssignment, TaskSubmission
from app.services.task_service import assign_task, submit_result

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/task", response_model=TaskAssignment | None)
async def get_task(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a task assignment for a device. Validates device ownership."""
    try:
        did = UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid device_id format")

    try:
        assignment = await assign_task(db, did, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if not assignment:
        return None

    # Emit event (server-side only, not user-controlled)
    event = Event(
        user_id=user.id,
        event_name="start_compute",
        device_id=did,
        job_id=assignment.job_id,
        metadata_json=json.dumps({
            "task_id": str(assignment.id),
            "device_id": device_id,
            "template_type": assignment.template_type,
        }),
    )
    db.add(event)
    user.last_active_at = datetime.now(timezone.utc)
    await db.commit()

    return assignment


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit(
    submission: TaskSubmission,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a computed result. Validation, scoring, event emission,
    and Torque forwarding are all handled inside submit_result()."""
    try:
        await submit_result(db, submission, user.id)
    except ValueError as e:
        detail = str(e)
        if "not belong" in detail:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
        if "Duplicate" in detail or "terminal state" in detail:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    return {"status": "accepted"}
