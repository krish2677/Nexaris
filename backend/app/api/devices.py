"""
Device API — register devices, send heartbeats.
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.device import Device, DeviceType
from app.models.user import User
from app.schemas.device import DeviceHeartbeat, DeviceRegister, DeviceResponse
from app.services.heartbeat_service import process_heartbeat

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    data: DeviceRegister,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a new compute device."""
    device = Device(
        user_id=user.id,
        device_type=DeviceType(data.device_type),
        cpu_cores=data.cpu_cores,
        ram=data.ram,
        device_power_factor=data.device_power_factor,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


@router.post("/heartbeat")
async def heartbeat(
    data: DeviceHeartbeat,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update device liveness. Validates device belongs to the user."""
    # Verify device ownership (prevents impersonation)
    device_q = await db.execute(
        select(Device).where(Device.id == data.device_id, Device.user_id == user.id)
    )
    if not device_q.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Device does not belong to you")
    await process_heartbeat(db, data.device_id, data.status)
    return {"status": "ok"}


@router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's registered devices."""
    result = await db.execute(select(Device).where(Device.user_id == user.id))
    return list(result.scalars().all())
