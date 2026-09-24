"""Host and Origin checks for a server that grants access without a credential.

With ``auth.enabled`` false, every request to the API is admin. A browser is
then the only thing between a web page the user visits and their KBs, and two
browser rules do not hold on their own:

- **Host.** A page on a name its owner controls can re-point that name at
  127.0.0.1. The browser then treats this server as same-origin with the page,
  so CORS never applies. The only thing such a request cannot fake is the
  ``Host`` it is addressed to, so a request must name a host this server
  expects, or it gets 421 and reaches no handler.
- **Origin.** CORS stops a page reading a response, not sending a simple
  request (a form post, a multipart upload, a body-less POST). A
  state-changing request whose ``Origin`` -- or, with no ``Origin``, whose
  ``Referer`` -- is neither this host nor configured in ``cors_origins`` gets
  403. Requests with neither header are not browser-initiated cross-site
  requests (CLI, curl, agents) and are unaffected.

A server with auth enabled is not restricted by this middleware: every useful
request there carries a credential a foreign page cannot supply (the session
cookie is ``SameSite=Lax``), and it typically sits behind a proxy with a
public hostname.

``origin_permitted`` is the one Origin rule; ``/ws`` uses it too.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Receive, Scope, Send

from ..config import PyriteConfig, Settings

logger = logging.getLogger(__name__)

# Loopback names a local install always answers. Tests add TestClient's
# "testserver" through the repo-wide conftest; it is deliberately not here.
LOCAL_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1"})

_WILDCARD_BIND_HOSTS = frozenset({"", "0.0.0.0", "::"})
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _hostname(value: str) -> str:
    """``host[:port]`` (or ``[v6]:port``) -> lowercase host, no brackets or port."""
    value = value.strip().lower()
    if value.startswith("["):
        return value[1:].split("]", 1)[0]
    if value.count(":") == 1:
        return value.split(":", 1)[0]
    return value


def allowed_hosts(settings: Settings) -> set[str]:
    """Every hostname this server answers while it grants credential-free access."""
    hosts = set(LOCAL_HOSTS)
    bind = _hostname(settings.host or "")
    if bind not in _WILDCARD_BIND_HOSTS:
        hosts.add(bind)
    hosts.update(_hostname(h) for h in settings.allowed_hosts)
    return hosts


def origin_permitted(origin: str, host: str, cors_origins: list[str]) -> bool:
    """An ``Origin`` value is this server's own host or configured in ``cors_origins``.

    ``"*"`` in ``cors_origins`` is not a wildcard here: REST drops credentials
    for a wildcard origin, and this rule exists for requests whose authority is
    ambient (a cookie, or no credential at all).
    """
    if origin in cors_origins:
        return True
    netloc = urlsplit(origin).netloc
    return bool(host) and netloc.lower() == host.lower()


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return None


def _request_origin(scope: Scope) -> str | None:
    """The request's ``Origin``, or the origin part of its ``Referer``."""
    origin = _header(scope, b"origin")
    if origin is not None:
        return origin
    referer = _header(scope, b"referer")
    if referer is None:
        return None
    parts = urlsplit(referer)
    return f"{parts.scheme}://{parts.netloc}"


class RequestGuardMiddleware:
    """ASGI middleware applying the Host and Origin rules above.

    Covers every HTTP route and WebSocket handshake of the app it wraps,
    including the ``/mcp`` mount and ``/ws``. Reads config per request so a
    test or an admin reload that swaps ``app.state.pyrite_config`` is honoured.
    """

    def __init__(self, app: ASGIApp, get_config: Callable[[], PyriteConfig]) -> None:
        self.app = app
        self.get_config = get_config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        settings = self.get_config().settings
        if settings.auth.enabled:
            await self.app(scope, receive, send)
            return

        host = _header(scope, b"host") or ""
        if _hostname(host) not in allowed_hosts(settings):
            logger.warning(
                "Refused request to %s: Host %r is not an allowed host "
                "(add it to settings.allowed_hosts to serve on that name)",
                scope.get("path"),
                host,
            )
            await _refuse(scope, send, 421, "Misdirected request: host not allowed")
            return

        if scope["type"] == "http" and scope["method"] not in _SAFE_METHODS:
            origin = _request_origin(scope)
            if origin is not None and not origin_permitted(origin, host, settings.cors_origins):
                logger.warning(
                    "Refused cross-origin %s %s from %r", scope["method"], scope.get("path"), origin
                )
                await _refuse(scope, send, 403, "Cross-origin request refused")
                return

        await self.app(scope, receive, send)


async def _refuse(scope: Scope, send: Send, status: int, detail: str) -> None:
    if scope["type"] == "websocket":
        # Closing before accept makes the server answer the handshake with 403.
        await send({"type": "websocket.close", "code": 1008})
        return
    body = json.dumps({"detail": detail}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
