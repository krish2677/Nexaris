"""
Request signing middleware for replay protection.
Verifies HMAC-SHA256 signatures and prevents request replay attacks
using nonce + timestamp validation stored in Redis.

IMPORTANT: This middleware caches the request body and reconstructs
the ASGI receive callable so that downstream handlers (FastAPI/Pydantic)
can still read the body. Without this, BaseHTTPMiddleware's body
consumption would cause 422 errors or empty-body failures.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# How long (seconds) a request timestamp is considered valid
REQUEST_VALIDITY_WINDOW = 300  # 5 minutes
# Nonce TTL in Redis (slightly longer than validity window)
NONCE_TTL = 600


class ReplayProtectionMiddleware(BaseHTTPMiddleware):
    """
    Optional HMAC replay protection for sensitive endpoints.
    Clients must send:
      X-Request-Timestamp: <unix_timestamp>
      X-Request-Nonce: <unique_uuid>
      X-Request-Signature: <hmac_sha256_hex>

    Signature is computed as: HMAC-SHA256(secret_key, f"{method}:{path}:{timestamp}:{nonce}:{body}")

    If signing headers are absent, the request passes through unmodified.
    If signing headers are present but the signature is invalid, the request
    is logged but still allowed through (soft enforcement) since no client
    currently implements HMAC signing.
    """

    # Paths where signing is checked (when headers are present)
    PROTECTED_PATHS = frozenset({
        "/api/v1/tasks/submit",
        "/api/v1/events/",
    })

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Only check on protected paths
        if path not in self.PROTECTED_PATHS:
            return await call_next(request)

        # Check for signing headers
        timestamp = request.headers.get("X-Request-Timestamp")
        nonce = request.headers.get("X-Request-Nonce")
        signature = request.headers.get("X-Request-Signature")

        # If no signing headers, pass through (signing is opt-in)
        if not timestamp or not nonce or not signature:
            return await call_next(request)

        # ── Cache body bytes and rebuild receive so downstream can read it ──
        body = await request.body()
        # Reconstruct the receive callable so Starlette/FastAPI can re-read
        async def _receive():
            return {"type": "http.request", "body": body}
        request._receive = _receive

        # Validate timestamp freshness
        try:
            req_time = float(timestamp)
        except (ValueError, TypeError):
            logger.warning(f"Replay protection: invalid timestamp from {request.client}")
            return await call_next(request)  # Soft-fail

        if abs(time.time() - req_time) > REQUEST_VALIDITY_WINDOW:
            logger.warning(f"Replay protection: expired request ({time.time() - req_time:.0f}s old)")
            return await call_next(request)  # Soft-fail

        # Check nonce uniqueness (replay protection)
        try:
            redis = await get_redis()
            nonce_key = f"nonce:{nonce}"
            exists = await redis.exists(nonce_key)
            if exists:
                logger.warning(f"Replay protection: duplicate nonce {nonce}")
                return await call_next(request)  # Soft-fail — log but allow
            # Store nonce to prevent reuse
            await redis.setex(nonce_key, NONCE_TTL, "1")
        except Exception:
            pass  # Fail open if Redis is down

        # Verify HMAC signature (soft enforcement — log mismatch but allow)
        method = request.method
        expected_payload = f"{method}:{path}:{timestamp}:{nonce}:{body.decode()}"
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(),
            expected_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            logger.warning(
                f"Replay protection: HMAC mismatch on {method} {path} "
                f"(client={request.client}). Allowing through — soft enforcement."
            )
            # Soft-fail: allow the request through. JWT auth + device
            # ownership checks are the real authorization layer.

        return await call_next(request)
