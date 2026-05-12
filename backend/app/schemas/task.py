"""Task schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class TaskAssignment(BaseModel):
    id: UUID
    job_id: UUID
    template_type: str
    parameters_json: str
    range_start: Optional[int] = None
    range_end: Optional[int] = None
    chunk_reference: Optional[str] = None
    reward_multiplier: float


class TaskSubmission(BaseModel):
    task_id: UUID
    device_id: UUID
    result_json: str


class TaskResponse(BaseModel):
    id: UUID
    job_id: UUID
    status: str
    range_start: Optional[int] = None
    range_end: Optional[int] = None
    retry_count: int
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
