"""
Events API — emit custom events for MCP processing.
Restricts server-only event names from being emitted by clients.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventCreate

router = APIRouter(prefix="/events", tags=["events"])

# Events that can only be emitted server-side (never by a client)
_SERVER_ONLY_EVENTS = frozenset({
    "validated_work_unit_completed",
    "start_compute",
    "end_compute",
    "user_inactive",
    "dataset_priority_changed",
})

# Events that clients are allowed to emit
_ALLOWED_CLIENT_EVENTS = frozenset({
    "referral_completed",
    "feedback_submitted",
    "profile_updated",
})


@router.post("/", status_code=status.HTTP_201_CREATED)
async def emit_event(
    data: EventCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Emit a custom event. Server-only events are blocked."""
    if data.event_name in _SERVER_ONLY_EVENTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Event '{data.event_name}' can only be emitted by the server",
        )

    event = Event(
        user_id=user.id,
        event_name=data.event_name,
        metadata_json=data.metadata_json,
    )
    db.add(event)
    await db.commit()
    return {"status": "created", "event_id": str(event.id)}
