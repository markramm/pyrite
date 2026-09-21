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
import socket

import httpx
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


def _client_with(handler):
    """An AsyncClient factory that answers every request through `handler`."""
    real = httpx.AsyncClient

    def factory(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(**kwargs)

    return factory


def _public_dns(monkeypatch):
    """Make any hostname resolve to a public IP, so the first hop passes."""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )


class TestRedirectBypass:
    """A redirect to a blocked address is refused, not followed (#219).

    `_check_url_safe` guards the URL the caller supplies; before this change
    every hop after it was unchecked, because httpx followed redirects itself.
    """

    def test_redirect_to_loopback_is_refused(self, monkeypatch):
        _public_dns(monkeypatch)
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            _client_with(
                lambda request: httpx.Response(
                    302, headers={"Location": "http://127.0.0.1:8000/api/kbs"}
                )
            ),
        )

        with pytest.raises(ClipperBlockedHostError):
            _clip("https://evil.example/x")

    def test_redirect_to_link_local_metadata_is_refused(self, monkeypatch):
        _public_dns(monkeypatch)
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            _client_with(
                lambda request: httpx.Response(
                    302, headers={"Location": "http://169.254.169.254/latest/meta-data/"}
                )
            ),
        )

        with pytest.raises(ClipperBlockedHostError):
            _clip("https://evil.example/x")

    def test_the_refusal_matches_a_direct_block(self, monkeypatch):
        """Same exception type and error code as a URL blocked up front, so a
        caller cannot tell whether the internal host answered."""
        _public_dns(monkeypatch)
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            _client_with(
                lambda request: httpx.Response(302, headers={"Location": "http://10.0.0.1/"})
            ),
        )

        with pytest.raises(ClipperBlockedHostError) as via_redirect:
            _clip("https://evil.example/x")
        with pytest.raises(ClipperBlockedHostError) as direct:
            _clip("http://10.0.0.1/")

        assert via_redirect.value.error_code == direct.value.error_code

    def test_an_ordinary_redirect_is_still_followed(self, monkeypatch):
        """The hook must not break redirects to public addresses."""
        _public_dns(monkeypatch)

        def handler(request):
            if request.url.path == "/start":
                return httpx.Response(302, headers={"Location": "https://public.example/final"})
            return httpx.Response(200, text="<html><title>Final</title><body>ok</body></html>")

        monkeypatch.setattr(httpx, "AsyncClient", _client_with(handler))

        result = _clip("https://public.example/start")

        assert result.title == "Final"
