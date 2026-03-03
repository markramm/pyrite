"""Tests for MCP rate limiter."""

from unittest.mock import patch

import pytest

from pyrite.config import Settings
from pyrite.server.mcp_rate_limiter import MCPRateLimiter


@pytest.fixture
def settings():
    return Settings(
        rate_limit_read="5/second",
        rate_limit_write="3/second",
        rate_limit_admin="2/second",
    )


@pytest.fixture
def limiter(settings):
    return MCPRateLimiter(settings)


class TestParseLimit:
    def test_per_minute(self):
        assert MCPRateLimiter._parse_limit("100/minute") == (100, 60)

    def test_per_second(self):
        assert MCPRateLimiter._parse_limit("30/second") == (30, 1)

    def test_per_hour(self):
        assert MCPRateLimiter._parse_limit("10/hour") == (10, 3600)

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            MCPRateLimiter._parse_limit("bad")

    def test_invalid_unit(self):
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            MCPRateLimiter._parse_limit("10/day")


class TestAllowsWithinLimit:
    def test_allows_up_to_max(self, limiter):
        for i in range(5):
            allowed, info = limiter.check("client1", "read")
            assert allowed, f"Call {i + 1} should be allowed"
            assert info["remaining"] == 4 - i
            assert info["limit"] == 5

    def test_blocks_over_limit(self, limiter):
        for _ in range(5):
            limiter.check("client1", "read")

        allowed, info = limiter.check("client1", "read")
        assert not allowed
        assert info["remaining"] == 0
        assert info["retry_after"] > 0


class TestSeparateTiers:
    def test_independent_buckets(self, limiter):
        # Exhaust read bucket
        for _ in range(5):
            limiter.check("client1", "read")
        allowed_read, _ = limiter.check("client1", "read")
        assert not allowed_read

        # Write bucket should still work
        allowed_write, _ = limiter.check("client1", "write")
        assert allowed_write

    def test_independent_clients(self, limiter):
        # Exhaust client1's read bucket
        for _ in range(5):
            limiter.check("client1", "read")
        allowed_c1, _ = limiter.check("client1", "read")
        assert not allowed_c1

        # client2 should still work
        allowed_c2, _ = limiter.check("client2", "read")
        assert allowed_c2


class TestRefillAfterWindow:
    def test_refill(self, limiter):
        # Exhaust the bucket
        for _ in range(5):
            limiter.check("client1", "read")
        allowed, _ = limiter.check("client1", "read")
        assert not allowed

        # Advance time past window (1 second for our fixture)
        with patch("pyrite.server.mcp_rate_limiter.time") as mock_time:
            # First call set last_refill at some monotonic time; simulate 2s later
            mock_time.monotonic.return_value = (
                limiter._buckets[("client1", "read")].last_refill + 2.0
            )
            allowed, info = limiter.check("client1", "read")
            assert allowed
            assert info["remaining"] == 4  # max_calls(5) - 1


class TestExemptLocal:
    def test_exempt_setting(self):
        s = Settings(mcp_rate_limit_exempt_local=True)
        assert s.mcp_rate_limit_exempt_local is True

    def test_non_exempt_setting(self):
        s = Settings(mcp_rate_limit_exempt_local=False)
        assert s.mcp_rate_limit_exempt_local is False
