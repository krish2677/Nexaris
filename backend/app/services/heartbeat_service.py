"""
Heartbeat service — monitors worker liveness and device status.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.device import Device, DeviceStatus

logger = logging.getLogger(__name__)


async def process_heartbeat(db: AsyncSession, device_id, status: str) -> None:
    """Update device last_seen timestamp and status."""
    await db.execute(
        update(Device)
        .where(Device.id == device_id)
        .values(
            last_seen=datetime.now(timezone.utc),
            status=DeviceStatus(status) if status else DeviceStatus.ONLINE,
        )
    )
    await db.commit()


async def mark_stale_devices(db: AsyncSession) -> int:
    """Mark devices that haven't sent a heartbeat as offline."""
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=settings.HEARTBEAT_TIMEOUT_SECONDS
    )
    stmt = (
        update(Device)
        .where(
            and_(
                Device.status != DeviceStatus.OFFLINE,
                Device.last_seen < cutoff,
            )
        )
        .values(status=DeviceStatus.OFFLINE)
    )
    result = await db.execute(stmt)
    await db.commit()
    count = result.rowcount  # type: ignore[attr-defined]
    if count:
        logger.info(f"Marked {count} stale devices as offline")
    return count
