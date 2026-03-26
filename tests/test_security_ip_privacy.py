"""Tests for IP address privacy in the API server.

Verifies that client IP addresses are not stored or logged in a recoverable form.
"""

import pytest


class TestRateLimiterKeyFunction:
    """The rate limiter must not use raw IP addresses as keys."""

    def test_key_function_does_not_return_raw_ip(self):
        """The rate limiter key function should hash or anonymize the IP."""
        from pyrite.server.api import limiter

        # The key function should not be get_remote_address (which returns raw IPs)
        from slowapi.util import get_remote_address

        assert limiter._key_func is not get_remote_address, (
            "Rate limiter uses get_remote_address which exposes raw client IPs. "
            "Use a hashing key function instead."
        )

    def test_key_function_returns_hashed_value(self):
        """The key function should return a non-reversible hash, not the raw IP."""
        from unittest.mock import MagicMock

        from pyrite.server.api import limiter

        # Create a mock request with a known IP
        mock_request = MagicMock()
        mock_request.client.host = "203.0.113.42"
        mock_request.headers = {}

        result = limiter._key_func(mock_request)

        # Result should not contain the raw IP
        assert "203.0.113.42" not in result
        # Result should be consistent (same input → same output)
        result2 = limiter._key_func(mock_request)
        assert result == result2


class TestUvicornAccessLogSuppression:
    """Uvicorn access logs must be suppressed to prevent IP logging."""

    def test_api_module_does_not_use_default_access_log(self):
        """The uvicorn.run call should disable access logging."""
        import inspect

        from pyrite.server import api

        source = inspect.getsource(api)
        # Check that uvicorn.run calls include access_log=False
        # or use a log_config that suppresses access logs
        assert "access_log=False" in source or "log_config" in source, (
            "uvicorn.run() should be called with access_log=False to prevent "
            "client IP addresses from being logged."
        )
