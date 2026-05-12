"""
LeaderboardEntry model — cached ranking for fast retrieval.
"""

import uuid

from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    score = Column(Float, default=0.0)
    rank = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="leaderboard_entry")
