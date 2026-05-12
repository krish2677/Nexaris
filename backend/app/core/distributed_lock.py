"""
Distributed lock using Redis for multi-node safe background processing.
Ensures only one instance runs MCP engine, stale recovery, and leaderboard refresh.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class DistributedLock:
    """Redis-based distributed lock with auto-renewal."""

    def __init__(self, name: str, ttl_seconds: int = 60) -> None:
        self.name = f"desci:lock:{name}"
        self.ttl = ttl_seconds
        self._renew_task: Optional[asyncio.Task] = None
        self._held = False
        self._last_error_log = 0.0  # Suppress repeated error logs

    async def acquire(self) -> bool:
        """Try to acquire the lock. Returns True if acquired."""
        try:
            redis = await get_redis()
            # SET NX with expiry — atomic acquire
            acquired = await redis.set(self.name, "1", nx=True, ex=self.ttl)
            if acquired:
                self._held = True
                # Start background renewal
                self._renew_task = asyncio.create_task(self._auto_renew())
                return True
            return False
        except Exception as e:
            import time
            now = time.time()
            # Only log every 5 minutes to avoid spam when Redis is down
            if now - self._last_error_log > 300:
                logger.warning(f"Lock acquire error ({self.name}): {e} — Redis may be down, processing anyway")
                self._last_error_log = now
            return True  # Fail open — allow processing if Redis is down

    async def release(self) -> None:
        """Release the lock."""
        self._held = False
        if self._renew_task:
            self._renew_task.cancel()
            try:
                await self._renew_task
            except asyncio.CancelledError:
                pass
        try:
            redis = await get_redis()
            await redis.delete(self.name)
        except Exception:
            pass

    async def _auto_renew(self) -> None:
        """Renew lock TTL periodically while held."""
        while self._held:
            try:
                await asyncio.sleep(self.ttl // 3)
                if self._held:
                    redis = await get_redis()
                    await redis.expire(self.name, self.ttl)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def __aenter__(self):
        acquired = await self.acquire()
        if not acquired:
            raise RuntimeError(f"Could not acquire lock: {self.name}")
        return self

    async def __aexit__(self, *args):
        await self.release()


# Pre-configured locks for background tasks
mcp_lock = DistributedLock("mcp_engine", ttl_seconds=120)
stale_recovery_lock = DistributedLock("stale_recovery", ttl_seconds=90)
leaderboard_lock = DistributedLock("leaderboard_refresh", ttl_seconds=90)
