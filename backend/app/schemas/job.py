"""Job schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class JobCreate(BaseModel):
    name: str
    template_type: str
    parameters_json: str = "{}"
    priority: int = 1
    required_workers: int = 1
    validation_strategy: str = "duplicate"


class JobResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    template_type: str
    parameters_json: str
    priority: int
    reward_multiplier: float
    active_workers: int
    required_workers: int
    validation_strategy: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
