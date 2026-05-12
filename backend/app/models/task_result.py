"""
TaskResult model — stores computation output, validation status,
consensus selection, and execution metrics.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ValidationStatus(str, enum.Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    SPOT_CHECKED = "spot_checked"


class TaskResult(Base):
    __tablename__ = "task_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    result_json = Column(Text, nullable=False)
    execution_time_ms = Column(Integer, nullable=True)
    validation_status = Column(
        SQLEnum(ValidationStatus), default=ValidationStatus.PENDING
    )
    consensus_group = Column(String(64), nullable=True)
    checksum = Column(String(64), nullable=True)
    is_canonical = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    task = relationship("Task", back_populates="results")
    device = relationship("Device", back_populates="task_results")
