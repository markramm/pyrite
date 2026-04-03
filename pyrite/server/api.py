"""
FastAPI REST Server for pyrite

Provides HTTP API access to knowledge bases for web applications and external integrations.

All endpoints are served under the /api prefix. Endpoint implementations live in
the ``endpoints/`` subpackage; this module provides shared dependencies, the rate
limiter, and the application factory.
"""

import hashlib
import logging
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ..config import PyriteConfig, Settings, load_config
from ..services.ephemeral_service import EphemeralKBService
from ..services.export_service import ExportService
from ..services.graph_service import GraphService
from ..services.index_worker import IndexWorker
from ..services.kb_registry_service import KBRegistryService
from ..services.kb_service import KBService
from ..services.llm_service import LLMService
from ..services.review_service import ReviewService
from ..services.search_service import SearchService
from ..services.starred_service import StarredService
from ..services.version_service import VersionService
from ..storage.database import PyriteDB
from ..storage.index import IndexManager

logger = logging.getLogger(__name__)


def _anonymized_key_func(request: Request) -> str:
    """Hash the client IP for rate limiting without storing the raw address.

    Uses SHA-256 truncated to 16 chars — sufficient for rate limiting,
    not reversible to the original IP address.
    """
    raw_ip = get_remote_address(request)
    return hashlib.sha256(raw_ip.encode()).hexdigest()[:16]


# =============================================================================
# Dependencies (imported by endpoint modules)
#
# Service state lives on ``app.state.pyrite_*`` attributes, initialised by
# ``create_app()``.  DI functions read from app.state so each FastAPI app
# instance is fully isolated — no cross-test contamination via module globals.
# =============================================================================


def _init_app_state(application: FastAPI, config: PyriteConfig) -> None:
    """Initialise pyrite service state on *application*.state."""
    application.state.pyrite_config = config
    application.state.pyrite_db = None
    application.state.pyrite_index_mgr = None
    application.state.pyrite_index_worker = None
    application.state.pyrite_kb_service = None
    application.state.pyrite_kb_registry = None
    application.state.pyrite_llm_service = None
    application.state.pyrite_diff_db_cache = {}  # (user_id, kb_name) → PyriteDB


def get_config() -> PyriteConfig:
    """Get or load configuration.

    When used inside a FastAPI app created by ``create_app()``, this is
    overridden via ``dependency_overrides`` to return the app-state config.
    Direct calls (non-DI contexts) fall back to ``load_config()``.
    """
    return load_config()


def get_db() -> PyriteDB:
    """Get or create database connection.

    When used inside a FastAPI app created by ``create_app()``, this is
    overridden via ``dependency_overrides`` to return the app-state DB.
    Direct calls (non-DI contexts) create a fresh connection.
    """
    config = load_config()
    return PyriteDB(config.settings.index_path)


def get_index_mgr() -> IndexManager:
    """Get or create index manager.

    Overridden via ``dependency_overrides`` inside FastAPI apps.
    """
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    return IndexManager(db, config)


def get_index_worker() -> IndexWorker:
    """Get or create index worker.

    Overridden via ``dependency_overrides`` inside FastAPI apps.
    """
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    return IndexWorker(db, config)


def get_kb_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> KBService:
    """Get or create KB service via DI."""
    return KBService(config, db)


def get_worktree_resolver(
    request: Request,
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
):
    """Get a WorktreeResolver for per-user read/write routing."""
    from .worktree_resolver import WorktreeResolver

    # Cache diff DBs on app state to avoid heavyweight re-init per request
    cache = getattr(request.app.state, "pyrite_diff_db_cache", {})
    return WorktreeResolver(config, db, cache)


def get_llm_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> LLMService:
    """Get or create LLM service, using DB settings with config file fallback."""
    provider = db.get_setting("ai.provider") or config.settings.ai_provider
    api_key = db.get_setting("ai.apiKey") or config.settings.ai_api_key
    model = db.get_setting("ai.model") or config.settings.ai_model
    base_url = db.get_setting("ai.baseUrl") or config.settings.ai_api_base
    # Default base URL for Gemini's OpenAI-compatible endpoint
    if provider == "gemini" and not base_url:
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    settings = Settings(
        ai_provider=provider,
        ai_api_key=api_key,
        ai_model=model,
        ai_api_base=base_url,
    )
    return LLMService(settings)


def get_kb_registry(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
    index_mgr: IndexManager = Depends(get_index_mgr),
) -> KBRegistryService:
    """Get KBRegistryService instance via DI."""
    return KBRegistryService(config, db, index_mgr)


def get_repo_service(
    request: Request,
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
):
    """Get RepoService, injecting the current user's GitHub token if available."""
    from ..services.repo_service import RepoService

    svc = RepoService(config, db)

    # Inject user's stored GitHub token if available
    auth_user = getattr(request, "state", None) and getattr(request.state, "auth_user", None)
    if auth_user:
        from ..services.auth_service import AuthService

        auth_service = AuthService(db, config.settings.auth)
        gh_token, _ = auth_service.get_github_token_for_user(auth_user["id"])
        if gh_token:
            svc._github_token = gh_token
        else:
            svc._github_token = None
    else:
        svc._github_token = None

    return svc


def get_graph_service(
    db: PyriteDB = Depends(get_db),
) -> GraphService:
    """Get GraphService instance via DI."""
    return GraphService(db)


def get_export_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> ExportService:
    """Get ExportService instance via DI."""
    return ExportService(config, db)


def get_ephemeral_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> EphemeralKBService:
    """Get EphemeralKBService instance via DI."""
    return EphemeralKBService(config, db)


def get_review_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> ReviewService:
    """Get ReviewService instance via DI."""
    return ReviewService(config, db)


def get_version_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> VersionService:
    """Get VersionService instance via DI."""
    return VersionService(config, db)


def get_search_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> SearchService:
    """Get SearchService instance via DI."""
    return SearchService(db, settings=config.settings)


def get_starred_service(
    db: PyriteDB = Depends(get_db),
    kb_service: KBService = Depends(get_kb_service),
) -> StarredService:
    """Get StarredService instance via DI."""
    return StarredService(db, kb_service)


def invalidate_llm_service():
    """Reset the cached LLM service so next request rebuilds it.

    No-op retained for import compatibility. With app-state-scoped DI,
    LLM services are rebuilt per-request from current DB settings.
    """


TIER_LEVELS = {"read": 0, "write": 1, "admin": 2}


def resolve_api_key_role(key: str | None, config: PyriteConfig) -> str | None:
    """Resolve an API key to its role (read/write/admin).

    Returns:
        - "admin" when auth is disabled (no api_key and no api_keys)
        - "admin" when key matches the legacy single api_key
        - The configured role when key hash matches an api_keys entry
        - None when key is invalid or missing (auth enabled but key wrong)
    """
    import hashlib

    has_single_key = bool(config.settings.api_key)
    has_key_list = bool(config.settings.api_keys)

    # No auth configured → everyone is admin
    if not has_single_key and not has_key_list:
        return "admin"

    if not key:
        return None

    # Check api_keys list first (takes precedence)
    if has_key_list:
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        for entry in config.settings.api_keys:
            if secrets.compare_digest(key_hash, entry.get("key_hash", "")):
                return entry.get("role", "read")

    # Fall back to legacy single api_key (grants admin)
    # Compare via hash to avoid holding plaintext key in config memory
    if has_single_key:
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        stored_hash = hashlib.sha256(config.settings.api_key.encode()).hexdigest()
        if secrets.compare_digest(key_hash, stored_hash):
            return "admin"

    return None


async def verify_api_key(
    request: Request,
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
):
    """Verify API key, session cookie, or anonymous tier. Stores role in request.state.

    Checks in order:
    1. X-API-Key header / api_key query param (existing behaviour)
    2. Session cookie (web UI auth)
    3. Anonymous tier (configurable public access)
    4. No auth configured → admin (backwards-compatible)
    """
    # 1. API key (header or query param)
    key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if key:
        role = resolve_api_key_role(key, config)
        if role is not None:
            request.state.api_role = role
            return

    # 2. Session cookie (when auth enabled)
    if config.settings.auth.enabled:
        token = request.cookies.get("pyrite_session")
        if token:
            from ..services.auth_service import AuthService

            auth_service = AuthService(db, config.settings.auth)
            user = auth_service.verify_session(token)
            if user:
                request.state.api_role = user["role"]
                request.state.auth_user = user
                return

    # 3. Anonymous tier
    if config.settings.auth.enabled and config.settings.auth.anonymous_tier:
        request.state.api_role = config.settings.auth.anonymous_tier
        return

    # 4. No auth configured → admin (existing behavior)
    if (
        not config.settings.api_key
        and not config.settings.api_keys
        and not config.settings.auth.enabled
    ):
        request.state.api_role = "admin"
        return

    raise HTTPException(status_code=401, detail="Invalid or missing API key")


def requires_tier(tier: str):
    """FastAPI dependency factory: enforce minimum tier on an endpoint.

    Usage: router = APIRouter(dependencies=[Depends(requires_tier("admin"))])
    """

    async def _check_tier(request: Request):
        role = getattr(request.state, "api_role", None)
        if role is None:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        if TIER_LEVELS.get(role, -1) < TIER_LEVELS.get(tier, 99):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions: requires '{tier}' tier, your role is '{role}'",
            )

    return _check_tier


async def _resolve_kb_name(request: Request) -> str | None:
    """Extract KB name from request via query params, path params, or body."""
    # 1. Query param (used by DELETE, import, export)
    kb = request.query_params.get("kb")
    if kb:
        return kb

    # 2. Path param (used by admin KB endpoints like /kbs/{name}/permissions)
    name = request.path_params.get("name")
    if name:
        return name

    # 3. Parse request body for "kb" key
    try:
        body = await request.body()
        if body:
            import json

            data = json.loads(body)
            if isinstance(data, dict):
                return data.get("kb")
    except Exception:
        logger.warning("Failed to extract KB from request body", exc_info=True)

    return None


def resolve_kb_default_role(config: PyriteConfig, db: PyriteDB, kb_name: str) -> str | None:
    """Resolve a KB's default_role from config or DB.

    Config takes precedence; falls back to DB for user-registered KBs.
    """
    kb_config = config.get_kb(kb_name)
    if kb_config and kb_config.default_role is not None:
        return kb_config.default_role
    row = db._raw_conn.execute("SELECT default_role FROM kb WHERE name = ?", (kb_name,)).fetchone()
    return row[0] if row else None


def requires_kb_tier(tier: str):
    """FastAPI dependency factory: enforce minimum tier on a per-KB basis.

    Resolution chain:
    1. Global admins always pass
    2. Explicit KB grant → KB default_role → user global role → anonymous tier

    Falls back to global role check when KB name cannot be resolved.
    """

    async def _check_kb_tier(
        request: Request,
        config: PyriteConfig = Depends(get_config),
        db: PyriteDB = Depends(get_db),
    ):
        role = getattr(request.state, "api_role", None)
        if role is None:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

        # Global admins always pass
        if role == "admin":
            return

        # If no authenticated user (API key mode), fall back to global role check
        auth_user = getattr(request.state, "auth_user", None)
        if not auth_user:
            if TIER_LEVELS.get(role, -1) < TIER_LEVELS.get(tier, 99):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions: requires '{tier}' tier, your role is '{role}'",
                )
            return

        # Resolve KB name from request
        kb_name = await _resolve_kb_name(request)
        if not kb_name:
            # Fall back to global tier check
            if TIER_LEVELS.get(role, -1) < TIER_LEVELS.get(tier, 99):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions: requires '{tier}' tier, your role is '{role}'",
                )
            return

        kb_default_role = resolve_kb_default_role(config, db, kb_name)

        from ..services.auth_service import AuthService

        auth_service = AuthService(db, config.settings.auth)
        effective_role = auth_service.get_kb_role(auth_user["id"], kb_name, kb_default_role)

        if effective_role is None or TIER_LEVELS.get(effective_role, -1) < TIER_LEVELS.get(
            tier, 99
        ):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions on KB '{kb_name}': requires '{tier}' tier",
            )

    return _check_kb_tier


# =============================================================================
# Content Negotiation
# =============================================================================


def negotiate_response(request: Request, data: Any) -> Response | None:
    """Check Accept header and return formatted response, or None for default JSON.

    Endpoints call this after computing their result dict. If the client
    requested a non-JSON format via the Accept header, returns a Response
    with the serialized content. Returns None when JSON is acceptable so
    the endpoint can use its normal Pydantic response model.
    """
    accept = request.headers.get("accept", "application/json")

    # Skip negotiation for standard JSON requests
    if not accept or accept == "*/*" or "application/json" in accept.split(",")[0]:
        return None

    from ..formats import format_response, negotiate_format

    fmt = negotiate_format(accept)
    if fmt is None:
        return JSONResponse(
            status_code=406,
            content={
                "error": "Not Acceptable",
                "supported_formats": [
                    "application/json",
                    "text/markdown",
                    "text/csv",
                    "text/yaml",
                ],
            },
        )

    if fmt == "json":
        return None  # Use default

    content, media_type = format_response(data, fmt)
    return Response(content=content, media_type=media_type)


# =============================================================================
# Rate Limiter
# =============================================================================

limiter = Limiter(key_func=_anonymized_key_func)


# =============================================================================
# Application Factory
# =============================================================================


def create_app(config: PyriteConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Optional config to use. If None, loads from default config file.
    """
    from fastapi import APIRouter

    from .endpoints import all_routers

    application = FastAPI(
        title="pyrite API",
        description="REST API for pyrite knowledge management",
        version="0.12.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Resolve config for CORS setup
    if config is None:
        config = load_config()

    # Store all service state on app.state for per-app isolation
    _init_app_state(application, config)

    # Override DI functions to read from app.state instead of module globals
    def _app_get_config() -> PyriteConfig:
        return application.state.pyrite_config

    def _app_get_db() -> PyriteDB:
        if application.state.pyrite_db is None:
            cfg = application.state.pyrite_config
            db = PyriteDB(cfg.settings.index_path)
            application.state.pyrite_db = db
            # Merge DB-registered KBs into config so all code paths see them
            try:
                from sqlalchemy import text
                rows = db.session.execute(
                    text("SELECT name, path, kb_type, description FROM kb WHERE source = 'user'")
                ).fetchall()
                if rows:
                    db_kbs = [{"name": r[0], "path": r[1], "kb_type": r[2], "description": r[3] or ""} for r in rows]
                    cfg.merge_db_kbs(db_kbs)
            except Exception:
                pass  # Table may not exist yet on first startup
        return application.state.pyrite_db

    def _app_get_index_mgr() -> IndexManager:
        if application.state.pyrite_index_mgr is None:
            application.state.pyrite_index_mgr = IndexManager(_app_get_db(), _app_get_config())
        return application.state.pyrite_index_mgr

    def _app_get_kb_registry() -> KBRegistryService:
        if application.state.pyrite_kb_registry is None:
            application.state.pyrite_kb_registry = KBRegistryService(
                _app_get_config(), _app_get_db(), _app_get_index_mgr()
            )
        return application.state.pyrite_kb_registry

    def _app_get_index_worker() -> IndexWorker:
        if application.state.pyrite_index_worker is None:
            worker = IndexWorker(_app_get_db(), _app_get_config())

            # Wire WebSocket broadcast for progress updates.
            # NOTE: This callback is invoked from IndexWorker's background
            # thread, not the main asyncio thread.  get_running_loop() will
            # raise RuntimeError when no loop is active in the calling thread,
            # which is the expected case — we catch it silently.
            def _ws_progress(job_id: str, current: int, total: int):
                import asyncio

                from .websocket import manager

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        manager.broadcast(
                            {
                                "type": "index_progress",
                                "job_id": job_id,
                                "current": current,
                                "total": total,
                            }
                        )
                    )
                except RuntimeError:
                    pass

            worker.on_progress = _ws_progress
            application.state.pyrite_index_worker = worker
        return application.state.pyrite_index_worker

    application.dependency_overrides[get_config] = _app_get_config
    application.dependency_overrides[get_db] = _app_get_db
    application.dependency_overrides[get_index_mgr] = _app_get_index_mgr
    application.dependency_overrides[get_index_worker] = _app_get_index_worker
    application.dependency_overrides[get_kb_registry] = _app_get_kb_registry

    # Seed config KBs into DB registry
    try:
        registry = _app_get_kb_registry()
        seeded = registry.seed_from_config()
        if seeded:
            logger.info("Seeded %d config KB(s) into registry", seeded)
    except Exception:
        logger.warning("Failed to seed KB registry from config", exc_info=True)

    # Set up embedding service for prewarm (actual prewarm happens in lifespan)
    if config.settings.prewarm_embeddings:
        from ..services.embedding_service import EmbeddingService

        application.state.pyrite_embedding_svc = EmbeddingService(
            _app_get_db(), model_name=config.settings.embedding_model
        )

    # CORS — use configured origins; disable credentials with wildcard (spec compliance)
    origins = config.settings.cors_origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    application.state.limiter = limiter
    application.add_exception_handler(
        RateLimitExceeded,
        lambda request, exc: JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {exc.detail}"},
            headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
        ),
    )

    # Auth router (mounted outside /api, no verify_api_key dependency)
    from .auth_endpoints import auth_router

    application.include_router(auth_router)

    # Collect endpoint routers under /api with auth + read-tier baseline
    api_router = APIRouter(
        prefix="/api",
        dependencies=[Depends(verify_api_key), Depends(requires_tier("read"))],
    )
    for r in all_routers:
        api_router.include_router(r)
    application.include_router(api_router)

    # Health check (not behind /api — used for infra probes, no rate limit)
    @application.get("/health", tags=["Admin"])
    def health_check():
        """Health check endpoint."""
        result: dict[str, Any] = {
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if config.settings.prewarm_embeddings:
            svc = getattr(application.state, "pyrite_embedding_svc", None)
            result["embeddings"] = {
                "ready": svc.is_warm if svc else False,
            }
        return result

    # WebSocket endpoint for multi-tab awareness
    @application.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        from .websocket import manager

        await manager.connect(ws)
        try:
            while True:
                # Keep connection alive; clients can send pings
                await ws.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(ws)

    # Mount static files if dist directory exists
    # Check env override first (for containerised deploys where the package is
    # installed as a site-package and the relative path won't resolve).
    dist_dir = (
        Path(os.environ.get("PYRITE_STATIC_DIR", ""))
        if os.environ.get("PYRITE_STATIC_DIR")
        else None
    )
    if dist_dir is None:
        dist_dir = Path(__file__).parent.parent.parent / "web" / "dist"
    # Always mount /site and /viewer routes (independent of SPA dist)
    from .static import mount_site_routes

    mount_site_routes(application)

    # Mount SPA static files if dist directory exists
    if dist_dir.is_dir():
        from .static import mount_static

        mount_static(application, dist_dir)

    return application


# =============================================================================
# Default application instance (used by uvicorn / existing imports)
# =============================================================================

app = create_app()


# =============================================================================
# Main
# =============================================================================


def main():
    """Run the API server."""
    import uvicorn

    config = load_config()
    uvicorn.run(
        "pyrite.server.api:app",
        host=config.settings.host,
        port=config.settings.port,
        access_log=False,
    )


if __name__ == "__main__":
    main()
