"""
WebSocket hub — real-time broadcast with JWT authentication
for leaderboard, rewards, worker counts, MCP events, and job status changes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Set, Optional

from fastapi import WebSocket, Query

from app.core.security import verify_token

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections with auth and channel-based broadcasts."""

    def __init__(self) -> None:
        self._channels: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self, websocket: WebSocket, channel: str = "global", token: Optional[str] = None
    ) -> bool:
        """Accept WebSocket with optional JWT authentication."""
        # Authenticate if token provided
        if token:
            payload = verify_token(token)
            if payload is None:
                await websocket.close(code=4001, reason="Invalid token")
                return False

        await websocket.accept()
        async with self._lock:
            if channel not in self._channels:
                self._channels[channel] = set()
            self._channels[channel].add(websocket)
        logger.info(f"WS connected to '{channel}' ({len(self._channels[channel])} clients)")
        return True

    async def disconnect(self, websocket: WebSocket, channel: str = "global") -> None:
        async with self._lock:
            if channel in self._channels:
                self._channels[channel].discard(websocket)
                if not self._channels[channel]:
                    del self._channels[channel]

    async def broadcast(self, channel: str, message: dict) -> None:
        """Broadcast a JSON message to all clients on a channel."""
        async with self._lock:
            clients = list(self._channels.get(channel, set()))

        if not clients:
            return

        payload = json.dumps(message)
        dead: list[WebSocket] = []

        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._channels.get(channel, set()).discard(ws)

    async def broadcast_all(self, message: dict) -> None:
        """Broadcast to every channel."""
        async with self._lock:
            channels = list(self._channels.keys())
        for ch in channels:
            await self.broadcast(ch, message)

    @property
    def connection_count(self) -> int:
        return sum(len(s) for s in self._channels.values())


# Singleton
ws_manager = ConnectionManager()
