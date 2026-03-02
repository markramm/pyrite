"""In-memory token bucket rate limiter for the MCP server."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass

from ..config import Settings

_LIMIT_RE = re.compile(r"^(\d+)/(second|minute|hour)$")
_UNIT_SECONDS = {"second": 1, "minute": 60, "hour": 3600}


@dataclass
class _Bucket:
    max_calls: int
    window: float
    tokens: int = 0
    last_refill: float = 0.0

    def __post_init__(self):
        self.tokens = self.max_calls
        self.last_refill = time.monotonic()


class MCPRateLimiter:
    """Per-client, per-tier token bucket rate limiter."""

    def __init__(self, settings: Settings) -> None:
        self._limits: dict[str, tuple[int, float]] = {
            "read": self._parse_limit(settings.rate_limit_read),
            "write": self._parse_limit(settings.rate_limit_write),
            "admin": self._parse_limit(settings.rate_limit_admin),
        }
        self._buckets: dict[tuple[str, str], _Bucket] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _parse_limit(spec: str) -> tuple[int, float]:
        m = _LIMIT_RE.match(spec)
        if not m:
            raise ValueError(
                f"Invalid rate limit format: {spec!r}  (expected '<int>/<second|minute|hour>')"
            )
        return int(m.group(1)), _UNIT_SECONDS[m.group(2)]

    def check(self, client_id: str, tier: str) -> tuple[bool, dict]:
        max_calls, window = self._limits[tier]
        key = (client_id, tier)

        with self._lock:
            bucket = self._buckets.get(key)
            now = time.monotonic()

            if bucket is None:
                bucket = _Bucket(max_calls=max_calls, window=window)
                bucket.last_refill = now
                self._buckets[key] = bucket

            elapsed = now - bucket.last_refill
            if elapsed >= bucket.window:
                bucket.tokens = bucket.max_calls
                bucket.last_refill = now

            if bucket.tokens > 0:
                bucket.tokens -= 1
                return True, {
                    "remaining": bucket.tokens,
                    "limit": bucket.max_calls,
                    "retry_after": 0,
                }

            retry_after = round(bucket.window - elapsed, 1)
            return False, {
                "remaining": 0,
                "limit": bucket.max_calls,
                "retry_after": max(retry_after, 0.1),
            }
