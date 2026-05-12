"""
AggregatedResult model — persisted aggregation outputs for completed jobs.
Supports incremental aggregation with versioning and checkpointing.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class AggregationStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"


class AggregatedResult(Base):
    __tablename__ = "aggregated_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    aggregation_version = Column(Integer, default=1)
    metrics_json = Column(Text, nullable=False, default="{}")
    completed_tasks = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    aggregation_status = Column(
        SQLEnum(AggregationStatus), default=AggregationStatus.IN_PROGRESS
    )
    checkpoint_json = Column(Text, default="{}")
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
