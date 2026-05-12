"""
Device model — represents a compute contributor's machine.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class DeviceStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    COMPUTING = "computing"
    IDLE = "idle"


class DeviceType(str, enum.Enum):
    ANDROID = "android"
    DESKTOP = "desktop"
    SERVER = "server"


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_type = Column(SQLEnum(DeviceType), nullable=False)
    device_power_factor = Column(Float, default=1.0)
    cpu_cores = Column(Integer, default=1)
    ram = Column(Integer, default=1024)
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.OFFLINE)
    last_seen = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="devices")
    tasks = relationship("Task", back_populates="assigned_device")
    task_results = relationship("TaskResult", back_populates="device")
