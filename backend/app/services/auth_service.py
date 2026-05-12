"""
Authentication service — registration, login, token management.
"""

from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.leaderboard import LeaderboardEntry
from app.models.user import User
from app.schemas.auth import TokenResponse, UserRegister


async def register_user(db: AsyncSession, data: UserRegister) -> User:
    """Create a new user account with a unique referral code."""
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise ValueError("Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        wallet_address=data.wallet_address,
        referral_code=secrets.token_urlsafe(8),
        referred_by=data.referral_code,
    )
    db.add(user)
    await db.flush()

    # Create leaderboard entry
    entry = LeaderboardEntry(user_id=user.id, score=0.0, rank=0)
    db.add(entry)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> TokenResponse | None:
    """Verify credentials and return a JWT token."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return None

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
    )


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
