"""Tests for the web clipper SSRF defense (r1300 clipper-ssrf-defense).

The clipper takes a user-supplied URL and fetches it server-side. Without
SSRF defense, any authenticated user can ask the server to fetch
http://127.0.0.1/, http://169.254.169.254/, or any private-range IP —
reaching internal services or instance-metadata endpoints from the
server's network position.

These tests pin the contract: any URL whose resolved host is on the
blocklist (loopback, link-local, private RFC1918, reserved, IPv6
equivalents) is rejected BEFORE any HTTP request is made.

Tests are sync wrappers using asyncio.run because the existing test
suite has no async fixtures wired up.
"""

from __future__ import annotations

import asyncio

import pytest

from pyrite.exceptions import ClipperBlockedHostError
from pyrite.services.clipper import ClipperService


def _clip(url: str):
    """Synchronous wrapper so tests stay flat."""
    svc = ClipperService()
    return asyncio.run(svc.clip_url(url))


class TestSSRFDefense:
    """Reject URLs whose host resolves to a blocked IP."""

    def test_localhost_v4_literal_rejected(self):
        """http://127.0.0.1/ must be rejected without an HTTP call."""
        with pytest.raises(ClipperBlockedHostError):
            _clip("http://127.0.0.1/")

    def test_localhost_v6_literal_rejected(self):
        """http://[::1]/ must be rejected."""
        with pytest.raises(ClipperBlockedHostError):
            _clip("http://[::1]/")

    def test_localhost_hostname_rejected(self):
        """The hostname `localhost` resolves to loopback and must be rejected."""
        with pytest.raises(ClipperBlockedHostError):
            _clip("http://localhost/")

    def test_private_rfc1918_10_block_rejected(self):
        """http://10.0.0.1/ (RFC1918 private) must be rejected."""
        with pytest.raises(ClipperBlockedHostError):
            _clip("http://10.0.0.1/")

    def test_private_rfc1918_192_block_rejected(self):
        """http://192.168.1.1/ (RFC1918 private) must be rejected."""
        with pytest.raises(ClipperBlockedHostError):
            _clip("http://192.168.1.1/")

    def test_private_rfc1918_172_block_rejected(self):
        """http://172.16.0.1/ (RFC1918 private) must be rejected."""
        with pytest.raises(ClipperBlockedHostError):
            _clip("http://172.16.0.1/")

    def test_link_local_aws_metadata_rejected(self):
        """http://169.254.169.254/ (AWS instance metadata) must be rejected.

        This is the highest-impact SSRF target on hosted infrastructure —
        a metadata endpoint hit can yield instance credentials. Other
        providers (GCP, Azure, DigitalOcean) use similar 169.254.0.0/16
        addresses.
        """
        with pytest.raises(ClipperBlockedHostError):
            _clip("http://169.254.169.254/latest/meta-data/")

    def test_unspecified_v4_rejected(self):
        """http://0.0.0.0/ (unspecified) must be rejected."""
        with pytest.raises(ClipperBlockedHostError):
            _clip("http://0.0.0.0/")

    def test_non_http_scheme_rejected(self):
        """file:// and ftp:// schemes must be rejected — only http(s) allowed."""
        with pytest.raises(ClipperBlockedHostError):
            _clip("file:///etc/passwd")

    def test_error_carries_stable_error_code(self):
        """ClipperBlockedHostError exposes a stable error_code so REST/MCP
        handlers can surface a stable identifier per the ticket
        acceptance criterion."""
        with pytest.raises(ClipperBlockedHostError) as excinfo:
            _clip("http://127.0.0.1/")
        assert excinfo.value.error_code == "CLIPPER_BLOCKED_HOST"
