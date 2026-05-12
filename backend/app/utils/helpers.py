"""Miscellaneous utility functions."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sign_payload(payload: dict, secret: str) -> str:
    """Create an HMAC-SHA256 signature for a JSON payload."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()


def verify_signature(payload: dict, signature: str, secret: str) -> bool:
    """Verify an HMAC-SHA256 signature."""
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)
