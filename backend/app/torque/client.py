"""
Torque Protocol client — leaderboards, rewards, raffles, campaigns,
and LIVE custom_events for real-time Torque integration.
Implements retry logic, failure recovery, and circuit breaker.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAY = 1  # seconds
REQUEST_TIMEOUT = 5  # seconds (was 30, way too long)

# Status codes where retrying is pointless
NON_RETRYABLE_CODES = frozenset({400, 401, 403, 404, 422, 530})

# Circuit breaker: disable Torque for N seconds after consecutive failures
CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_COOLDOWN = 300  # 5 minutes


class TorqueClient:
    """Async client for Torque Protocol REST API with custom_events support.
    Includes circuit breaker to prevent repeated failures from blocking the app."""

    def __init__(self) -> None:
        self.base_url = settings.TORQUE_API_URL
        self.api_key = settings.TORQUE_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0  # Unix timestamp

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is tripped."""
        if self._consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            if time.time() < self._circuit_open_until:
                return True
            # Cooldown expired, reset
            self._consecutive_failures = 0
        return False

    async def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic and circuit breaker."""
        if not self.api_key:
            return {"status": "skipped", "reason": "no_api_key"}

        if self._is_circuit_open():
            logger.debug(f"Torque circuit breaker open, skipping {method} {path}")
            return {"status": "circuit_open"}

        url = f"{self.base_url}{path}"
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.request(
                        method, url, json=payload, headers=self.headers
                    )
                    resp.raise_for_status()
                    self._consecutive_failures = 0  # Reset on success
                    return resp.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                status_code = e.response.status_code
                logger.warning(
                    f"Torque API {method} {path} attempt {attempt} failed: {status_code}"
                )
                # Don't retry on non-retryable status codes
                if status_code in NON_RETRYABLE_CODES:
                    self._consecutive_failures += 1
                    if self._consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
                        self._circuit_open_until = time.time() + CIRCUIT_BREAKER_COOLDOWN
                        logger.warning(
                            f"Torque circuit breaker OPEN for {CIRCUIT_BREAKER_COOLDOWN}s "
                            f"after {self._consecutive_failures} consecutive failures"
                        )
                    return {"status": "error", "code": status_code}
            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    f"Torque API {method} {path} attempt {attempt} connection error: {e}"
                )

            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)

        self._consecutive_failures += 1
        if self._consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_open_until = time.time() + CIRCUIT_BREAKER_COOLDOWN
            logger.warning(
                f"Torque circuit breaker OPEN for {CIRCUIT_BREAKER_COOLDOWN}s "
                f"after {self._consecutive_failures} consecutive failures"
            )

        logger.error(f"Torque API {method} {path} failed after {MAX_RETRIES} retries")
        return {"status": "error", "reason": "exhausted_retries"}

    # ── Custom Events (CRITICAL for hackathon) ──

    async def send_custom_event(
        self,
        user_pubkey: str,
        event_name: str,
        data: Dict[str, Any] | None = None,
    ) -> dict:
        """Send a real-time custom_event to Torque.

        Events like:
        - validated_work_unit_completed
        - job_under_supplied
        - user_returned_after_inactivity
        - researcher_created_job
        - contributor_reached_streak
        - high_priority_job_completed
        """
        return await self._request(
            "POST",
            "/v1/events",
            {
                "userPubkey": user_pubkey,
                "eventName": event_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data or {},
            },
        )

    # ── Leaderboard ──

    async def update_leaderboard(self, entries: list[dict]) -> dict:
        return await self._request(
            "POST",
            "/v1/leaderboard/update",
            {"entries": entries},
        )

    # ── Rewards ──

    async def send_reward_event(
        self, user_id: str, event_type: str, amount: float, metadata: dict | None = None
    ) -> dict:
        return await self._request(
            "POST",
            "/v1/rewards/event",
            {
                "user_id": user_id,
                "event_type": event_type,
                "amount": amount,
                "metadata": metadata or {},
            },
        )

    # ── Raffles ──

    async def create_raffle_entry(
        self, user_id: str, raffle_id: str, tickets: int = 1
    ) -> dict:
        return await self._request(
            "POST",
            "/v1/raffles/enter",
            {
                "user_id": user_id,
                "raffle_id": raffle_id,
                "tickets": tickets,
            },
        )

    # ── Campaigns ──

    async def trigger_campaign(
        self, campaign_id: str, user_ids: list[str], metadata: dict | None = None
    ) -> dict:
        return await self._request(
            "POST",
            "/v1/campaigns/trigger",
            {
                "campaign_id": campaign_id,
                "user_ids": user_ids,
                "metadata": metadata or {},
            },
        )

    # ── Gifts (retention) ──

    async def send_gift(
        self, user_pubkey: str, gift_type: str, amount: float = 0
    ) -> dict:
        return await self._request(
            "POST",
            "/v1/gifts/send",
            {
                "userPubkey": user_pubkey,
                "giftType": gift_type,
                "amount": amount,
            },
        )

    # ── Health ──

    async def health_check(self) -> bool:
        try:
            result = await self._request("GET", "/v1/health")
            return result.get("status") != "error"
        except Exception:
            return False


# Singleton instance
torque_client = TorqueClient()
