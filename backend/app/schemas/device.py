"""Device schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DeviceRegister(BaseModel):
    device_type: str
    cpu_cores: int = 1
    ram: int = 1024
    device_power_factor: float = 1.0


class DeviceHeartbeat(BaseModel):
    device_id: UUID
    status: str
    cpu_load: Optional[float] = None
    memory_usage: Optional[float] = None


class DeviceResponse(BaseModel):
    id: UUID
    device_type: str
    device_power_factor: float
    cpu_cores: int
    ram: int
    status: str
    last_seen: datetime

    class Config:
        from_attributes = True
