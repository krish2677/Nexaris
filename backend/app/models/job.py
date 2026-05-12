"""
Job model — a computational workload submitted by a researcher.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TemplateType(str, enum.Enum):
    MONTE_CARLO = "monte_carlo"
    DATASET_STATS = "dataset_stats"
    MATRIX_COMPUTE = "matrix_compute"


class ValidationStrategy(str, enum.Enum):
    DUPLICATE = "duplicate"
    DETERMINISTIC = "deterministic"
    SPOT_CHECK = "spot_check"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    template_type = Column(SQLEnum(TemplateType), nullable=False)
    parameters_json = Column(Text, default="{}")
    priority = Column(Integer, default=1)
    reward_multiplier = Column(Float, default=1.0)
    active_workers = Column(Integer, default=0)
    required_workers = Column(Integer, default=1)
    validation_strategy = Column(
        SQLEnum(ValidationStrategy), default=ValidationStrategy.DUPLICATE
    )
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    owner = relationship("User", back_populates="jobs")
    tasks = relationship("Task", back_populates="job", cascade="all, delete-orphan")
