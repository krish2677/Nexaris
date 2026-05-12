"""
Campaign model — enhanced campaign lifecycle supporting all 9 campaign types
with full metadata for the autonomous orchestration engine.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CampaignType(str, enum.Enum):
    SUPPLY_BALANCING = "supply_balancing"
    RETENTION = "retention"
    STREAK = "streak"
    NEW_CONTRIBUTOR = "new_contributor"
    REFERRAL = "referral"
    DATASET_COMPLETION = "dataset_completion"
    RELIABILITY = "reliability"
    TIME_BASED = "time_based"
    EXPERIMENTAL = "experimental"


class CampaignPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CampaignLifecycle(str, enum.Enum):
    PROPOSED = "proposed"       # AI proposed, awaiting budget check
    ACTIVE = "active"           # Funded and running
    PAUSED = "paused"           # Temporarily paused
    COMPLETED = "completed"     # Finished successfully
    EXPIRED = "expired"         # Duration elapsed
    CANCELLED = "cancelled"     # Manually or auto-cancelled
    FAILED = "failed"           # Budget insufficient or trigger invalid


class IncentiveCampaign(Base):
    """Full-lifecycle campaign created by the autonomous orchestration engine."""
    __tablename__ = "incentive_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    campaign_type = Column(String(50), nullable=False, index=True)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="proposed", index=True)

    # AI reasoning
    reasoning = Column(Text, nullable=True)
    target_audience = Column(String(255), nullable=True)

    # Budget
    reward_pool = Column(Float, default=0.0)
    spent = Column(Float, default=0.0)
    max_per_user = Column(Float, default=100.0)

    # Timing
    duration_hours = Column(Integer, default=24)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # Torque integration
    torque_primitives_json = Column(Text, default="[]")  # ["leaderboard", "raffle", "gift"]
    torque_campaign_id = Column(String(255), nullable=True)

    # Rules & metrics
    eligibility_rules_json = Column(Text, default="[]")
    success_metrics_json = Column(Text, default="[]")
    performance_json = Column(Text, default="{}")  # {"participants": 0, "conversions": 0, ...}

    # Targeting
    target_job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    target_dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)

    # Multiplier for reward boosts
    multiplier = Column(Float, default=1.0)

    # Source
    source = Column(String(30), default="rule_engine")  # "rule_engine", "llm", "manual"
    created_by_cycle = Column(Integer, default=0)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
