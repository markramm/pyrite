"""Rate limits for the unauthenticated auth endpoints.

``/auth/login`` is limited per client (every attempt) and per username
(failed attempts only, so a user signing in on several devices is not held
back by their own successes); ``/auth/register`` per client. The limits come
from ``settings.auth`` in the `limits` syntax slowapi uses.

Separate from the app-wide slowapi ``limiter``: that one keys on the request
alone, and the per-username limit needs the parsed body. One instance lives
on ``app.state``, so each app -- each test's app included -- counts on its own.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request
from limits import RateLimitItem, parse_many
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from ..config import AuthConfig


@dataclass
class _Limits:
    login_client: list[RateLimitItem]
    login_username: list[RateLimitItem]
    register_client: list[RateLimitItem]


class AuthRateLimiter:
    def __init__(self, auth_config: AuthConfig):
        self._limits = _Limits(
            login_client=parse_many(auth_config.login_rate_limit),
            login_username=parse_many(auth_config.login_rate_limit_per_username),
            register_client=parse_many(auth_config.register_rate_limit),
        )
        self._strategy = MovingWindowRateLimiter(MemoryStorage())

    def _refuse(self, items: list[RateLimitItem], *keys: str) -> None:
        reset = max(self._strategy.get_window_stats(item, *keys).reset_time for item in items)
        retry_after = max(1, math.ceil(reset - time.time()))
        raise HTTPException(
            status_code=429,
            detail="Too many attempts; try again later",
            headers={"Retry-After": str(retry_after)},
        )

    def _hit_all(self, items: list[RateLimitItem], *keys: str) -> None:
        """Count one attempt against every window; refuse when any is full."""
        if not all(self._strategy.test(item, *keys) for item in items):
            self._refuse(items, *keys)
        for item in items:
            self._strategy.hit(item, *keys)

    def check_login(self, client: str, username: str) -> None:
        """Before a login attempt: count it for the client, and refuse if the
        client or the username has used up its budget. Raises 429."""
        self._hit_all(self._limits.login_client, "login-client", client)
        if not all(
            self._strategy.test(item, "login-username", username)
            for item in self._limits.login_username
        ):
            self._refuse(self._limits.login_username, "login-username", username)

    def record_login_failure(self, username: str) -> None:
        for item in self._limits.login_username:
            self._strategy.hit(item, "login-username", username)

    def check_register(self, client: str) -> None:
        self._hit_all(self._limits.register_client, "register-client", client)


def get_auth_rate_limiter(request: Request, auth_config: AuthConfig) -> AuthRateLimiter:
    state = request.app.state
    limiter = getattr(state, "pyrite_auth_rate_limiter", None)
    if limiter is None:
        limiter = AuthRateLimiter(auth_config)
        state.pyrite_auth_rate_limiter = limiter
    return limiter
