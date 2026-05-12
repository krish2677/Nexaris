"""
Treasury model — tracks the network's reward budget, allocation percentages,
and spend history for autonomous campaign funding decisions.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class AllocationCategory(str, enum.Enum):
    RETENTION = "retention"
    SUPPLY_BALANCING = "supply_balancing"
    REFERRAL = "referral"
    STREAK = "streak"
    EXPERIMENTAL = "experimental"
    EMERGENCY = "emergency"


class TreasuryLedger(Base):
    """Single-row treasury state — tracks the overall budget pool."""
    __tablename__ = "treasury_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    total_balance = Column(Float, default=100_000.0, nullable=False)
    reserved_emergency = Column(Float, default=10_000.0, nullable=False)
    allocated_retention = Column(Float, default=0.0)
    allocated_supply = Column(Float, default=0.0)
    allocated_referral = Column(Float, default=0.0)
    allocated_streak = Column(Float, default=0.0)
    allocated_experimental = Column(Float, default=0.0)
    total_spent = Column(Float, default=0.0)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def available_balance(self) -> float:
        return max(self.total_balance - self.reserved_emergency - self.total_spent, 0.0)

    @property
    def utilization_rate(self) -> float:
        if self.total_balance <= 0:
            return 0.0
        return round(self.total_spent / self.total_balance, 4)


class TreasuryTransaction(Base):
    """Individual spend record tied to a campaign."""
    __tablename__ = "treasury_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), nullable=True)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(512), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
