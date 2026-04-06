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
import secrets
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request
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

    Returns a dict with keys: role, username, user_id (optional).
    Raises HTTPException(401) on failure.
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
    """Resolve an API key to its role (read/write/admin)."""
    has_single_key = bool(config.settings.api_key)
    has_key_list = bool(config.settings.api_keys)

    if not has_single_key and not has_key_list:
        return "admin"

    if not key:
        return None

    key_hash = hashlib.sha256(key.encode()).hexdigest()

    if has_key_list:
        for entry in config.settings.api_keys:
            if secrets.compare_digest(key_hash, entry.get("key_hash", "")):
                return entry.get("role", "read")

    if has_single_key:
        stored_hash = hashlib.sha256(config.settings.api_key.encode()).hexdigest()
        if secrets.compare_digest(key_hash, stored_hash):
            return "admin"

    return None


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

    # The SSE transport expects a relative path for the message endpoint.
    # Clients POST to this path with a session_id query parameter.
    sse_transport = SseServerTransport("/mcp/messages/")

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
        db = app_get_db()

        try:
            user_ctx = _resolve_bearer_auth(request, config, db)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )

        role = user_ctx["role"]
        client_id = user_ctx["username"]
        tier = role if role in ("read", "write", "admin") else "read"

        logger.info("MCP SSE connection: user=%s tier=%s", client_id, tier)

        mcp_server = _get_mcp_server(tier)
        sdk = mcp_server.build_sdk_server(client_id=client_id)

        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as (read_stream, write_stream):
            await sdk.run(
                read_stream, write_stream, sdk.create_initialization_options()
            )

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
        db = app_get_db()

        base_url = str(request.base_url).rstrip("/")
        endpoint_url = f"{base_url}/mcp/sse"

        info: dict[str, Any] = {
            "endpoint": endpoint_url,
            "transport": "sse",
            "auth": "bearer",
        }

        # Try to resolve user context for tier-specific info
        try:
            user_ctx = _resolve_bearer_auth(request, config, db)
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
