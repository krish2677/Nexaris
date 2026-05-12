"""Auth request / response schemas."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    wallet_address: Optional[str] = None
    referral_code: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    wallet_address: Optional[str] = None
    total_score: float
    referral_code: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
