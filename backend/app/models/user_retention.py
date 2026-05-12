"""
UserRetentionState model — tracks contributor engagement, streaks, and churn risk.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserRetentionState(Base):
    __tablename__ = "user_retention_state"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    streak_days = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    inactivity_score = Column(Float, default=0.0)
    churn_risk_score = Column(Float, default=0.0)
    total_validated_tasks = Column(Integer, default=0)
    reliability_score = Column(Float, default=1.0)
    last_reward_at = Column(DateTime(timezone=True), nullable=True)
    last_compute_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="retention_state")
