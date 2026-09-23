"""WebSocket connection manager for multi-tab awareness.

Every socket is authenticated at the handshake and carries the set of KBs its
owner may read (#218). An event naming a KB goes only to sockets that may read
it; an event naming none (``kb_synced``) goes to every accepted socket.

The readable set is resolved **once, at connect**, and fixed for the life of
the connection: a revoked grant or a logged-out session takes effect when the
socket reconnects. Events carry metadata only (KB name, entry id), and
re-resolving per event would put a DB walk per socket per event on the loop.
"""

import json
import logging
from typing import Any
from urllib.parse import urlsplit

from fastapi import HTTPException, WebSocket
from starlette.requests import HTTPConnection

from ..config import PyriteConfig
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


class HandshakeRejectedError(Exception):
    """The socket's credential (or lack of one) does not admit it."""


def origin_allowed(conn: HTTPConnection, config: PyriteConfig) -> bool:
    """A handshake's ``Origin`` is absent, the server's own host, or configured.

    CORS does not apply to WebSockets: a page on any site can open a socket to
    this server and the browser attaches the ``pyrite_session`` cookie
    (SameSite=lax admits it on a same-site cross-origin handshake, and
    non-browser clients send whatever they like). Once the cookie
    authenticates the socket, this is the only cross-origin gate.

    Absent ``Origin`` is allowed: browsers always send it on a WebSocket
    handshake, so its absence means a non-browser client, which the
    credential check alone governs. ``"*"`` in ``cors_origins`` is **not** a
    wildcard here: REST drops credentials for a wildcard origin, and this
    check exists precisely because a socket's credential is a cookie.
    """
    origin = conn.headers.get("origin")
    if origin is None:
        return True
    if origin in config.settings.cors_origins:
        return True
    host = conn.headers.get("host", "")
    netloc = urlsplit(origin).netloc
    return bool(host) and netloc.lower() == host.lower()


def resolve_socket_scope(
    conn: HTTPConnection, config: PyriteConfig, db: PyriteDB
) -> set[str] | None:
    """The KBs a handshake's caller may read; None when unscoped.

    Synchronous and may touch the DB (session lookup, grants): run it off the
    event loop. Outcomes match REST's ``verify_api_key``:

    - an operator API key (header, or the ``api_key`` query parameter, since
      a browser cannot set headers on a WebSocket) -- unscoped;
    - a valid session (cookie, or Bearer) -- scoped to that user;
    - no usable credential, auth enabled with an ``anonymous_tier`` -- scoped
      to what an anonymous visitor may read;
    - auth disabled and no keys configured -- unscoped (the default local
      install, unchanged);
    - otherwise ``HandshakeRejectedError``.

    Identity comes from ``mcp_routes._resolve_credential`` and the rule from
    ``api.readable_kbs_for_user`` -- no third implementation of either.
    """
    from .api import readable_kbs_for_user, resolve_api_key_role
    from .mcp_routes import _resolve_credential

    settings = config.settings

    # An operator key, which `resolve_api_key_role` accepts only when keys are
    # configured or auth is disabled (#331).
    key = conn.query_params.get("api_key")
    if key and resolve_api_key_role(key, config) is not None:
        return None

    try:
        ctx = _resolve_credential(conn, config, db)
    except HTTPException:
        ctx = None

    if ctx is not None and ctx.get("user_id") is not None:
        return readable_kbs_for_user(config, db, ctx["user_id"], ctx["role"])
    if ctx is not None:
        return None  # an operator key, or auth disabled with no keys

    if settings.auth.enabled and settings.auth.anonymous_tier:
        return readable_kbs_for_user(config, db, None, settings.auth.anonymous_tier)
    raise HandshakeRejectedError


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts events.

    Each connection maps to its readable set (``None`` = unscoped), resolved
    once at connect; ``broadcast`` filters on it without touching the DB.
    """

    def __init__(self):
        self._connections: dict[WebSocket, set[str] | None] = {}

    async def connect(self, ws: WebSocket, readable: set[str] | None):
        """Accept an *already authenticated* socket with its readable set."""
        await ws.accept()
        self._connections[ws] = readable
        logger.debug("WebSocket connected, total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket):
        self._connections.pop(ws, None)
        logger.debug("WebSocket disconnected, total: %d", len(self._connections))

    async def broadcast(self, event: dict[str, Any]):
        """Send an event to every connected socket that may read its KB."""
        if not self._connections:
            return
        kb_name = event.get("kb_name")
        message = json.dumps(event)
        dead: list[WebSocket] = []
        for ws, readable in list(self._connections.items()):
            if kb_name and readable is not None and kb_name not in readable:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.pop(ws, None)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


def broadcast_event(event_type: str, **data):
    """Broadcast a WebSocket event, swallowing errors if no event loop is running.

    Safe to call from sync endpoints and CLI contexts where no event loop exists.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast({"type": event_type, **data}))
    except RuntimeError:
        pass  # No event loop (CLI context, sync test, etc.)
