"""
FastAPI REST Server for pyrite

Provides HTTP API access to knowledge bases for web applications and external integrations.

All endpoints are served under the /api prefix. Endpoint implementations live in
the ``endpoints/`` subpackage; this module provides shared dependencies, the rate
limiter, and the application factory.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ..config import PyriteConfig, Settings, load_config
from ..services.kb_service import KBService
from ..services.llm_service import LLMService
from ..storage.database import PyriteDB
from ..storage.index import IndexManager

# =============================================================================
# Dependencies (imported by endpoint modules)
# =============================================================================

_config: PyriteConfig | None = None
_db: PyriteDB | None = None
_index_mgr: IndexManager | None = None
_kb_service: KBService | None = None
_llm_service: LLMService | None = None


def get_config() -> PyriteConfig:
    """Get or load configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_db() -> PyriteDB:
    """Get or create database connection."""
    global _db
    if _db is None:
        config = get_config()
        _db = PyriteDB(config.settings.index_path)
    return _db


def get_index_mgr() -> IndexManager:
    """Get or create index manager."""
    global _index_mgr
    if _index_mgr is None:
        _index_mgr = IndexManager(get_db(), get_config())
    return _index_mgr


def get_kb_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> KBService:
    """Get or create KB service. Uses FastAPI DI so test overrides work."""
    global _kb_service
    if _kb_service is None:
        _kb_service = KBService(config, db)
    # If config/db changed (test overrides), rebuild
    elif _kb_service.config is not config or _kb_service.db is not db:
        _kb_service = KBService(config, db)
    return _kb_service


def get_llm_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> LLMService:
    """Get or create LLM service, using DB settings with config file fallback."""
    global _llm_service
    if _llm_service is None:
        from ..services.kb_service import KBService  # noqa: N814

        svc = KBService(config, db)
        provider = svc.get_setting("ai.provider") or config.settings.ai_provider
        api_key = svc.get_setting("ai.apiKey") or config.settings.ai_api_key
        model = svc.get_setting("ai.model") or config.settings.ai_model
        base_url = svc.get_setting("ai.baseUrl") or config.settings.ai_api_base
        settings = Settings(
            ai_provider=provider,
            ai_api_key=api_key,
            ai_model=model,
            ai_api_base=base_url,
        )
        _llm_service = LLMService(settings)
    return _llm_service


def invalidate_llm_service():
    """Reset the cached LLM service so next request rebuilds it."""
    global _llm_service
    _llm_service = None


async def verify_api_key(request: Request, config: PyriteConfig = Depends(get_config)):
    """Verify API key if authentication is enabled.

    When config.settings.api_key is empty, auth is disabled (backwards-compatible).
    When set, requires X-API-Key header or api_key query param.
    """
    if not config.settings.api_key:
        return
    key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if key != config.settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


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

limiter = Limiter(key_func=get_remote_address)


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
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Resolve config for CORS setup
    if config is None:
        config = get_config()

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

    # Collect endpoint routers under /api with shared auth dependency
    api_router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])
    for r in all_routers:
        api_router.include_router(r)
    application.include_router(api_router)

    # Health check (not behind /api — used for infra probes, no rate limit)
    @application.get("/health", tags=["Admin"])
    def health_check():
        """Health check endpoint."""
        return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}

    # Mount static files if dist directory exists
    dist_dir = Path(__file__).parent.parent.parent / "web" / "dist"
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

    uvicorn.run("pyrite.server.api:app", host="127.0.0.1", port=8088)


if __name__ == "__main__":
    main()
