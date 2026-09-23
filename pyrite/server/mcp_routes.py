"""
MCP SSE transport routes for FastAPI.

Mounts the MCP SDK's SSE transport on the FastAPI app, enabling
Claude Desktop and Claude Code to connect over HTTP with Bearer token auth.

Endpoints:
    GET  /mcp/sse       — SSE connection (long-lived stream)
    POST /mcp/messages/ — client posts JSON-RPC messages
    GET  /mcp/info      — connection metadata for frontends
"""

import hashlib
import logging
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from ..config import PyriteConfig
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


def _resolve_bearer_auth(
    request: Request,
    config: PyriteConfig,
    db: PyriteDB,
) -> dict[str, Any]:
    """Validate Bearer token, X-API-Key header, or session cookie.

    Returns a dict with keys: role, username, user_id (optional),
    `readable_kbs` -- the KBs this caller may read -- and `writable_kbs` --
    the KBs a write-tier tool may target; each None when the caller is not
    scoped.

    The readable set comes from `api.readable_kbs_for_user`, the same helper
    the REST routes resolve through, so a grant honoured over REST is
    honoured over MCP and vice versa. There is deliberately no second
    implementation of the rule (#201).

    `user_id` is the discriminator, matching REST: non-None for a session
    user (scoped), None for an API key -- the operator's credential, not a
    peer's -- or for auth being disabled entirely, both unscoped.

    Raises HTTPException(401) on failure. Note there is no anonymous branch:
    `/mcp` 401s a caller with no credential where REST would admit them at
    `anonymous_tier`.
    """
    ctx = _resolve_credential(request, config, db)
    from .api import kbs_for_user_at_tier, readable_kbs_for_user

    scoped = ctx.get("user_id") is not None
    ctx["readable_kbs"] = readable_kbs_for_user(
        config, db, ctx.get("user_id"), ctx["role"], scoped=scoped
    )
    # The KBs a write-tier tool may target: the same per-KB rule REST's
    # `requires_kb_tier("write")` applies, resolved once per connection.
    ctx["writable_kbs"] = kbs_for_user_at_tier(
        config, db, ctx.get("user_id"), ctx["role"], "write", scoped=scoped
    )
    return ctx


def _resolve_credential(
    request: HTTPConnection,
    config: PyriteConfig,
    db: PyriteDB,
) -> dict[str, Any]:
    """The credential half of `_resolve_bearer_auth`: role, username, user_id.

    Reads only headers and cookies, so it takes any `HTTPConnection` -- a
    `Request` here, a `WebSocket` handshake in `websocket.resolve_socket_scope`
    (#218). One credential resolver for both transports, not two.

    Synchronous and may query the DB (session lookup): callers on the event
    loop run it in a threadpool.
    """
    # 1. Bearer token in Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            role = _resolve_api_key_role(token, config)
            if role is not None:
                key_id = hashlib.sha256(token.encode()).hexdigest()[:8]
                return {"role": role, "username": f"apikey-{key_id}", "user_id": None}

            # Check against session tokens (for web-authenticated users)
            if config.settings.auth.enabled:
                from ..services.auth_service import AuthService

                auth_service = AuthService(db, config.settings.auth)
                user = auth_service.verify_session(token)
                if user:
                    return {
                        "role": user["role"],
                        "username": user["username"],
                        "user_id": user["id"],
                    }

    # 2. X-API-Key header (fallback for clients that use it)
    api_key = request.headers.get("x-api-key")
    if api_key:
        role = _resolve_api_key_role(api_key, config)
        if role is not None:
            key_id = hashlib.sha256(api_key.encode()).hexdigest()[:8]
            return {"role": role, "username": f"apikey-{key_id}", "user_id": None}

    # 3. Session cookie
    if config.settings.auth.enabled:
        session_token = request.cookies.get("pyrite_session")
        if session_token:
            from ..services.auth_service import AuthService

            auth_service = AuthService(db, config.settings.auth)
            user = auth_service.verify_session(session_token)
            if user:
                return {
                    "role": user["role"],
                    "username": user["username"],
                    "user_id": user["id"],
                }

    # 4. No auth configured — open access
    if (
        not config.settings.api_key
        and not config.settings.api_keys
        and not config.settings.auth.enabled
    ):
        return {"role": "admin", "username": "anonymous", "user_id": None}

    raise HTTPException(
        status_code=401,
        detail="Invalid or missing authentication. Provide Authorization: Bearer <token> header.",
    )


def _resolve_api_key_role(key: str, config: PyriteConfig) -> str | None:
    """Resolve an API key to its role -- the REST rule, not a copy of it.

    There were two copies of this rule, and a bug in the "no keys configured"
    branch (any key answered "admin" with auth enabled) had to be fixed in
    both. Delegating keeps one implementation, as `readable_kbs_for_user` does.
    """
    from .api import resolve_api_key_role

    return resolve_api_key_role(key, config)


async def _authenticate(request: Request, config: PyriteConfig, shared_db: PyriteDB) -> dict:
    """Resolve the caller on a worker thread, with a per-request DB handle.

    The session lookup is synchronous DB work, so it runs off the event loop
    (as REST's ``verify_api_key`` does, #131) on a handle whose Session closes
    as soon as auth is resolved -- an SSE connection may stay open for hours
    and must not pin a pooled connection for its lifetime.
    """
    from starlette.concurrency import run_in_threadpool

    def _run() -> dict:
        with shared_db.request_handle() as db:
            return _resolve_bearer_auth(request, config, db)

    return await run_in_threadpool(_run)


def mount_mcp_routes(
    app: FastAPI,
    app_get_config: Callable[[], PyriteConfig],
    app_get_db: Callable[[], PyriteDB],
) -> None:
    """Mount MCP SSE transport endpoints on the FastAPI application.

    Uses Starlette-level routes for the SSE and message endpoints (which
    manage their own ASGI responses) and a standard FastAPI route for
    the /mcp/info metadata endpoint.
    """
    from mcp.server.sse import SseServerTransport

    from .mcp_server import PyriteMCPServer

    # SseServerTransport prepends scope["root_path"] (which is "/mcp" here,
    # since this whole app is nested under Mount("/mcp", ...) below) to this
    # endpoint to build the client-facing POST path. Passing "/mcp/messages/"
    # here double-prefixes it to "/mcp/mcp/messages/", which 404s — the
    # endpoint must be relative to the mount point, i.e. just "/messages/".
    sse_transport = SseServerTransport("/messages/")

    # Cache MCP server instances per tier to avoid repeated heavy init.
    _mcp_servers: dict[str, PyriteMCPServer] = {}

    def _get_mcp_server(tier: str) -> PyriteMCPServer:
        """Get or create MCP server for the given tier."""
        if tier not in _mcp_servers:
            config = app_get_config()
            _mcp_servers[tier] = PyriteMCPServer(config=config, tier=tier)
        return _mcp_servers[tier]

    # -----------------------------------------------------------------
    # GET /mcp/sse — long-lived SSE connection
    # -----------------------------------------------------------------

    async def handle_sse(request: Request) -> Response:
        """SSE endpoint for MCP client connections.

        Authenticates via Bearer token, resolves the user's tier,
        then hands off to the MCP SSE transport for the session lifetime.
        """
        config = app_get_config()
        try:
            user_ctx = await _authenticate(request, config, app_get_db())
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )

        role = user_ctx["role"]
        client_id = user_ctx["username"]
        tier = role if role in ("read", "write", "admin") else "read"
        readable = user_ctx["readable_kbs"]
        writable = user_ctx["writable_kbs"]

        logger.info(
            "MCP SSE connection: user=%s tier=%s scoped=%s",
            client_id,
            tier,
            readable is not None,
        )

        # The per-tier cache is untouched and its key stays `tier`: the
        # cached PyriteMCPServer is identity-free, and the readable set
        # rides the per-connection closures build_sdk_server already makes
        # for client_id. Two callers at one tier share this instance and
        # still get correctly different answers (#201).
        mcp_server = _get_mcp_server(tier)
        sdk = mcp_server.build_sdk_server(
            client_id=client_id, readable_kbs=readable, writable_kbs=writable
        )

        async with sse_transport.connect_sse(request.scope, request.receive, request._send) as (
            read_stream,
            write_stream,
        ):
            await sdk.run(read_stream, write_stream, sdk.create_initialization_options())

        # Return empty Response to avoid "NoneType not callable" on disconnect
        return Response()

    # -----------------------------------------------------------------
    # POST /mcp/messages/ — JSON-RPC message relay
    # -----------------------------------------------------------------
    # handle_post_message is a raw ASGI app; mount it directly.

    # -----------------------------------------------------------------
    # GET /mcp/info — connection metadata (normal JSON endpoint)
    # -----------------------------------------------------------------

    async def handle_info(request: Request) -> Response:
        """Return MCP connection info for frontends and documentation."""
        config = app_get_config()
        base_url = str(request.base_url).rstrip("/")
        endpoint_url = f"{base_url}/mcp/sse"

        info: dict[str, Any] = {
            "endpoint": endpoint_url,
            "transport": "sse",
            "auth": "bearer",
        }

        # Try to resolve user context for tier-specific info
        try:
            user_ctx = await _authenticate(request, config, app_get_db())
            tier = user_ctx["role"] if user_ctx["role"] in ("read", "write", "admin") else "read"
            mcp_server = _get_mcp_server(tier)
            info["tools_count"] = len(mcp_server.tools)
            info["tier"] = tier
        except HTTPException:
            # Unauthenticated — show basic info
            read_server = _get_mcp_server("read")
            info["tools_count"] = len(read_server.tools)
            info["tier"] = "unauthenticated"

        return JSONResponse(content=info)

    # -----------------------------------------------------------------
    # Mount all routes under /mcp
    # -----------------------------------------------------------------
    app.routes.insert(
        0,
        Mount(
            "/mcp",
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Route("/info", endpoint=handle_info, methods=["GET"]),
                Mount("/messages/", app=sse_transport.handle_post_message),
            ],
        ),
    )
