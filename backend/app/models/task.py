"""
Task model — an individual work unit within a job.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATING = "validating"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    assigned_device_id = Column(
        UUID(as_uuid=True), ForeignKey("devices.id"), nullable=True
    )
    range_start = Column(Integer, nullable=True)
    range_end = Column(Integer, nullable=True)
    chunk_reference = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)

    # Relationships
    job = relationship("Job", back_populates="tasks")
    assigned_device = relationship("Device", back_populates="tasks")
    results = relationship(
        "TaskResult", back_populates="task", cascade="all, delete-orphan"
    )
