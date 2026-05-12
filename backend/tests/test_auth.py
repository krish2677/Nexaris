"""
Tests for the auth endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@desci.network",
            "password": "strongpassword123",
            "wallet_address": "0xTestWallet",
        },
    )
    assert resp.status_code == 201
    user = resp.json()
    assert user["email"] == "test@desci.network"
    assert user["is_active"] is True

    # Login
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@desci.network",
            "password": "strongpassword123",
        },
    )
    assert resp.status_code == 200
    token = resp.json()
    assert "access_token" in token
    assert token["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@desci.network",
            "password": "wrongpassword",
        },
    )
    assert resp.status_code == 401
