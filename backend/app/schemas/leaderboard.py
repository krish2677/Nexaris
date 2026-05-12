"""Leaderboard schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class LeaderboardEntryResponse(BaseModel):
    user_id: UUID
    email: str
    score: float
    rank: int

    class Config:
        from_attributes = True
