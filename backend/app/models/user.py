"""
User model — contributors, researchers, and admins.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    wallet_address = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_active_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    total_score = Column(Float, default=0.0)
    referral_code = Column(String(20), unique=True, nullable=True)
    referred_by = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="owner", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")
    leaderboard_entry = relationship(
        "LeaderboardEntry", back_populates="user", uselist=False
    )
    retention_state = relationship(
        "UserRetentionState", back_populates="user", uselist=False
    )
