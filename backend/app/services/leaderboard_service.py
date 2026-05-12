"""
Leaderboard service — score updates and ranking.
"""

from __future__ import annotations

import logging
from typing import List

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leaderboard import LeaderboardEntry
from app.models.user import User

logger = logging.getLogger(__name__)


async def update_user_score(db: AsyncSession, user_id, delta: float) -> None:
    """Increment a user's total score and leaderboard entry."""
    await db.execute(
        update(User).where(User.id == user_id).values(total_score=User.total_score + delta)
    )
    # Upsert leaderboard entry
    result = await db.execute(
        select(LeaderboardEntry).where(LeaderboardEntry.user_id == user_id)
    )
    entry = result.scalar_one_or_none()
    if entry:
        entry.score += delta
    else:
        entry = LeaderboardEntry(user_id=user_id, score=delta)
        db.add(entry)
    await db.commit()


async def recalculate_ranks(db: AsyncSession) -> None:
    """Recalculate all leaderboard ranks based on score."""
    result = await db.execute(
        select(LeaderboardEntry).order_by(LeaderboardEntry.score.desc())
    )
    entries = list(result.scalars().all())
    for i, entry in enumerate(entries, 1):
        entry.rank = i
    await db.commit()
    logger.info(f"Recalculated ranks for {len(entries)} users")


async def get_leaderboard(
    db: AsyncSession, limit: int = 50
) -> List[dict]:
    """Get top N leaderboard entries with user info."""
    stmt = (
        select(LeaderboardEntry, User.email)
        .join(User, LeaderboardEntry.user_id == User.id)
        .order_by(LeaderboardEntry.rank.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "user_id": str(row[0].user_id),
            "email": row[1],
            "score": row[0].score,
            "rank": row[0].rank,
        }
        for row in rows
    ]
