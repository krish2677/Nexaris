"""
Leaderboard API — public leaderboard retrieval.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.leaderboard_service import get_leaderboard

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/")
async def leaderboard(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get the top contributors leaderboard."""
    entries = await get_leaderboard(db, limit=limit)
    return {"leaderboard": entries}
