"""
CampaignParticipant — tracks per-campaign contributor scores, ranks, and rewards.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CampaignParticipant(Base):
    __tablename__ = "campaign_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("incentive_campaigns.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    contribution_score = Column(Float, default=0.0)
    validated_units = Column(Integer, default=0)
    rank = Column(Integer, default=0)
    reward_earned_sol = Column(Float, default=0.0)
    reward_tx_signature = Column(String(255), nullable=True)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_score_at = Column(DateTime(timezone=True), nullable=True)


class WalletDeposit(Base):
    """On-chain SOL deposit record."""
    __tablename__ = "wallet_deposits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    wallet_address = Column(String(255), nullable=False)
    tx_signature = Column(String(255), unique=True, nullable=False)
    amount_sol = Column(Float, nullable=False)
    amount_lamports = Column(Float, nullable=True)
    status = Column(String(20), default="confirmed")  # pending, confirmed, failed
    category = Column(String(50), default="deposit")  # deposit, campaign_fund
    campaign_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RewardDistribution(Base):
    """Reward payout record from treasury to contributor."""
    __tablename__ = "reward_distributions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("incentive_campaigns.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    wallet_address = Column(String(255), nullable=False)
    amount_sol = Column(Float, nullable=False)
    tx_signature = Column(String(255), nullable=True)
    rank = Column(Integer, default=0)
    tier = Column(String(20), default="participation")  # top1, top3, top10, participation
    status = Column(String(20), default="pending")  # pending, sent, confirmed, failed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
