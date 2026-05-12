"""
MCPAction and RewardCampaign models — tracks MCP orchestration decisions
and active incentive campaigns.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ActionStatus(str, enum.Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CampaignStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class MCPAction(Base):
    __tablename__ = "mcp_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type = Column(String(100), nullable=False, index=True)
    target_job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    target_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    parameters_json = Column(Text, default="{}")
    status = Column(SQLEnum(ActionStatus), default=ActionStatus.PENDING)
    source = Column(String(20), default="rule_engine")  # "rule_engine" or "llm"
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class RewardCampaign(Base):
    __tablename__ = "reward_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_type = Column(String(100), nullable=False)
    multiplier = Column(Float, default=1.0)
    target_job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    start_time = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.ACTIVE)
    metadata_json = Column(Text, default="{}")
