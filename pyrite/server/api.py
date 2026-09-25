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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ..config import ConfigSaveRefusedError, PyriteConfig, Settings, load_config
from ..exceptions import (
    BrandingInvalidError,
    ConfigError,
    EntryNotFoundError,
    FrontmatterError,
    KBNotFoundError,
    KBProtectedError,
    KBReadOnlyError,
    LastAdminError,
    PluginError,
    PyriteError,
    QuerySyntaxError,
    QueryTooLongError,
    StorageError,
    ValidationError,
)
from ..services.ephemeral_service import EphemeralKBService
from ..services.export_service import ExportService
from ..services.graph_service import GraphService
from ..services.index_worker import IndexWorker
from ..services.kb_registry_service import KBRegistryService
from ..services.kb_service import KBService
from ..services.link_discovery_service import LinkDiscoveryService
from ..services.llm_service import LLMService
from ..services.llm_usage_service import LLMUsageService
from ..services.review_service import ReviewService
from ..services.search_service import SearchService
from ..services.starred_service import StarredService
from ..services.task_service import TaskService
from ..services.version_service import VersionService
from ..storage.database import PyriteDB
from ..storage.index import IndexManager

logger = logging.getLogger(__name__)


# Domain-exception → (HTTP status, error code) mapping for the central handler.
# Order matters: subclasses must precede their bases so isinstance() matches the
# most specific type first (e.g. FrontmatterError before ValidationError).
_PYRITE_ERROR_STATUS: list[tuple[type[PyriteError], int, str]] = [
    (EntryNotFoundError, 404, "ENTRY_NOT_FOUND"),
    (KBNotFoundError, 404, "KB_NOT_FOUND"),
    (KBReadOnlyError, 403, "KB_READ_ONLY"),
    (KBProtectedError, 403, "KB_PROTECTED"),
    (FrontmatterError, 422, "INVALID_FRONTMATTER"),
    (QueryTooLongError, 422, "QUERY_TOO_LONG"),
    (QuerySyntaxError, 400, "QUERY_SYNTAX"),
    # The one route that raises LastAdminError (PUT /auth/users/{id}/role)
    # catches it itself and re-raises as HTTPException, so this row is never
    # reached from there -- and its response shape differs from what this
    # row would produce: the route's HTTPException(detail={...}) nests as
    # {"detail": {"code", "message"}}, while this central handler returns
    # {"code", "message"} flat. This row exists so a *different*,
    # not-yet-written caller of AuthService.set_role -- one that lets
    # LastAdminError propagate instead of catching it -- still gets 409
    # LAST_ADMIN instead of falling through to the base ValidationError's
    # 422. Keep it above ValidationError so isinstance() matches it first.
    (LastAdminError, 409, "LAST_ADMIN"),
    (ValidationError, 422, "VALIDATION_ERROR"),
    (ConfigSaveRefusedError, 409, "CONFIG_SAVE_REFUSED"),
    (ConfigError, 409, "CONFIG_CONFLICT"),
    (PluginError, 502, "PLUGIN_ERROR"),
    (StorageError, 500, "STORAGE_ERROR"),
    # 500, not 409: this row governs the anonymous, always-public GET routes
    # that build a BrandingService as a side effect of serving content
    # (/config/branding, /sitemap.xml, /robots.txt) -- a broken branding.yaml
    # there is a server misconfiguration, not something wrong with the
    # caller's request. POST /api/site/render catches BrandingInvalidError
    # itself before this handler ever sees it and answers 409 (#408); this
    # row is unreached from that path.
    (BrandingInvalidError, 500, "BRANDING_INVALID"),
]


def register_pyrite_exception_handler(app: FastAPI) -> None:
    """Register a central handler mapping the PyriteError hierarchy to HTTP.

    Any PyriteError an endpoint does not catch itself is converted to a proper
    status code and a uniform ``{"code", "message"}`` JSON body, instead of
    leaking a raw 500 with a Python traceback. The message is the exception's
    own text — domain messages are written to be safe to show — and no
    traceback or internals are exposed. 5xx cases are logged with a traceback
    server-side for debugging.
    """

    def _classify(exc: PyriteError) -> tuple[int, str]:
        for exc_type, status_code, code in _PYRITE_ERROR_STATUS:
            if isinstance(exc, exc_type):
                return status_code, code
        return 500, "INTERNAL_ERROR"

    def _handler(request: Request, exc: PyriteError) -> JSONResponse:
        status_code, code = _classify(exc)
        if status_code >= 500:
            # The exception itself, not True: this handler runs outside the
            # except frame, so sys.exc_info() is empty here and exc_info=True
            # logged no traceback (#431).
            logger.error("Unhandled %s: %s", type(exc).__name__, exc, exc_info=exc)
        message = str(exc)
        public_message = getattr(exc, "public_message", None)
        if public_message is not None:
            # `str(exc)` may name a real filesystem path or other operator
            # detail unsafe to return over HTTP (#377's ConfigSaveRefusedError
            # pattern, extended to any PyriteError subclass that opts in via
            # a `public_message` class attribute -- e.g. BrandingInvalidError,
            # #445's cold read). Logged at the exception's own severity
            # already happened above for 5xx; a sub-500 refusal like this one
            # is worth a line too, since `message` below won't carry it.
            logger.warning("%s", exc)
            message = public_message
        return JSONResponse(status_code=status_code, content={"code": code, "message": message})

    app.add_exception_handler(PyriteError, _handler)


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
    application.state.pyrite_ws_loop = None
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


def _drain_embed_queue(db: PyriteDB, *, label: str = "") -> int:
    """Embed everything a write left in `embed_queue`. Blocking; never raises.

    Thin alias for `services.embedding_worker.settle_embed_queue`, which is
    the single drain implementation the CLI shares. Kept as a name in this
    module because the endpoints import it from here.
    """
    from ..services.embedding_worker import settle_embed_queue

    return settle_embed_queue(db, label=label)


def get_task_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> TaskService:
    """Get or create TaskService via DI."""
    return TaskService(config, db)


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


def get_llm_usage_service(
    db: PyriteDB = Depends(get_db),
) -> LLMUsageService:
    """Get or create LLMUsageService via DI."""
    return LLMUsageService(db)


def get_llm_service(
    request: Request,
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> LLMService:
    """Get or create LLM service, using DB settings with config file fallback.

    Wires the per-user usage-tracking context (llm-usage-tracking-and-
    quotas) when a request is authenticated -- anonymous access (auth
    disabled) records usage rows with user_id=None rather than skipping
    tracking entirely.
    """
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
    auth_user = getattr(request.state, "auth_user", None)
    user_id = auth_user["id"] if auth_user else None
    usage_service = LLMUsageService(db)
    return LLMService(settings, usage_service=usage_service, user_id=user_id)


def get_user_llm_context(
    request: Request,
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> dict | None:
    """Get the current user's LLM API key context, or None.

    Returns {"provider": ..., "api_key": ..., "model": ...} if the user
    has a stored BYOK key, otherwise None.
    """
    auth_user = getattr(request.state, "auth_user", None)
    if not auth_user:
        return None
    from ..services.auth_service import AuthService

    auth_svc = AuthService(db, config.settings.auth)
    return auth_svc.get_user_api_key(auth_user["id"])


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


def get_link_discovery_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> LinkDiscoveryService:
    """Get LinkDiscoveryService instance via DI."""
    return LinkDiscoveryService(config, db)


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
        - "admin" when no keys are configured and auth is disabled (open access)
        - None when no keys are configured and auth is enabled: no key is
          valid, so the caller falls through to its session or the anonymous
          tier (any key used to answer "admin" here)
        - "admin" when key matches the legacy single api_key
        - The configured role when key hash matches an api_keys entry
        - None when key is invalid or missing (auth enabled but key wrong)
    """
    import hashlib

    has_single_key = bool(config.settings.api_key)
    has_key_list = bool(config.settings.api_keys)

    # No keys configured: open access only when auth is also disabled.
    # With auth enabled there is no valid key, so any key is refused.
    if not has_single_key and not has_key_list:
        return None if config.settings.auth.enabled else "admin"

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

    This dependency is ``async``, so its body runs on the event-loop thread.
    Everything here must therefore be non-blocking — the one synchronous DB
    call (``AuthService.verify_session``) is offloaded with
    ``run_in_threadpool`` below (#131 criterion 4). Calling it inline both
    blocked the loop for the duration of the query and put event-loop DB work
    in the same session as the threadpool handlers' — the second, distinct
    exposure of the shared-session bug, specifically on the auth-enabled path.
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
            from starlette.concurrency import run_in_threadpool

            from ..services.auth_service import AuthService

            def _verify() -> dict | None:
                # Runs on a worker thread. `db` is this request's handle, so
                # the lookup uses this request's session — no scope to open,
                # and nothing shared with a concurrent request.
                auth_service = AuthService(db, config.settings.auth)
                return auth_service.verify_session(token)

            user = await run_in_threadpool(_verify)
            if user:
                request.state.api_role = user["role"]
                request.state.auth_user = user
                return

    # 3. Anonymous tier
    if config.settings.auth.enabled and config.settings.auth.anonymous_tier:
        request.state.api_role = config.settings.auth.anonymous_tier
        # Not an operator key: per-KB roles apply (a private KB is hidden).
        request.state.anonymous = True
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


# The parameter names that name a knowledge base, in every location a
# request can carry one. Pinned by tests/test_read_scoping_is_structural.py,
# which fails if a handler declares a KB-bearing parameter outside this set.
#
# `source_kb` and `target_kb` are the *secondary* KBs the `links.py` routes
# name alongside their primary one. They belong here rather than in a
# per-route allowlist: the rule is that naming two KBs gets both checked, so
# the only thing a route-specific exception would buy is a request that names
# a readable KB in one parameter and serves from a private one in the other
# (#186). `center_kb` is deliberately absent -- `/api/graph` filters nodes and
# edges by the readable set after building the graph, so a KB named there that
# the caller cannot read contributes nothing to the response, and checking it
# would turn a harmless name into a 404.
KB_PARAM_NAMES = ("kb", "kb_name", "source_kb", "target_kb")


class _UnparseableBodyError(Exception):
    """The request body could not be read or parsed, so the KBs it names are
    unknown. Never treated as "names no KB": that would make a guard pass."""


async def _resolve_kb_names(request: Request) -> list[str]:
    """Every KB this request names, in every location it can name one.

    Query parameters (every name in `KB_PARAM_NAMES` -- `reviews.py` binds
    `Query(..., alias="kb_name")`, so the wire name differs from the Python
    one), path parameters, and the JSON body's `kb`/`kb_name`. A route that
    takes a *secondary* KB (`source_kb`, `target_kb`) is therefore checked
    against that one too, not only against its primary.

    **Every** value is returned, never just the first. A request that names
    two KBs used to be checked against whichever spelling the resolver
    happened to read first and served from the other -- `kb` checked,
    `kb_name` served on the reviews routes; a `kb` query param checked, the
    path's `kb_name` served on `/api/kbs/{kb_name}` and `/orient`. Callers
    require *each* value to be permitted, which removes the whole class.

    Order is preserved and duplicates removed, so the first value is still
    a sensible single name for an error message.

    Raises `_UnparseableBodyError` when a **JSON** body cannot be parsed:
    "no KB named" is what lets a request through, so a body that was
    supposed to carry a KB and could not be read must not produce it.

    A body of any other content type is not read at all. Only a JSON object
    can name a KB the way this resolver understands, and a multipart upload
    (`/api/entries/import` binds `UploadFile = File(...)`) is consumed as a
    stream by FastAPI, so reading it here raises
    `RuntimeError("Stream consumed")` -- which is neither a malformed body
    nor an attack, and those routes name their KB in the query string
    anyway.
    """
    names: list[str] = []

    def add(value: object) -> None:
        if isinstance(value, str) and value and value not in names:
            names.append(value)

    # Path first: it is the route's own identity, the one location a caller
    # cannot add or remove. Only `kb`/`kb_name`; `/plugins/{name}` and
    # `/kbs/{name}` (admin) use `name` for other things, so `name` is read
    # only where the route is a KB route -- see `_admin_kb_path_name` below.
    for param in KB_PARAM_NAMES:
        add(request.path_params.get(param))
    add(_admin_kb_path_name(request))

    for param in KB_PARAM_NAMES:
        add(request.query_params.get(param))

    if not _has_json_body(request):
        return names

    try:
        body = await request.body()
    except Exception as exc:
        logger.warning("Failed to extract KB from request body", exc_info=True)
        raise _UnparseableBodyError() from exc
    if body:
        import json

        try:
            data = json.loads(body)
        except Exception as exc:
            logger.warning("Failed to extract KB from request body", exc_info=True)
            raise _UnparseableBodyError() from exc
        if isinstance(data, dict):
            for param in KB_PARAM_NAMES:
                add(data.get(param))

    return names


def _has_json_body(request: Request) -> bool:
    """Could this request's body be a JSON object naming a KB?

    Anything else -- a multipart upload, a form post, no body at all -- is
    left unread. The KB in those cases is in the path or the query, which
    the caller has already collected.
    """
    content_type = request.headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


def _admin_kb_path_name(request: Request) -> str | None:
    """The `{name}` path param, but only on routes where it names a KB.

    `admin.py` declares `/kbs/{name}` and `/kbs/{name}/permissions`; it also
    declares `/plugins/{name}`, where `name` is a plugin. Keying on the URL
    path keeps the plugin routes from being treated as KB routes.
    """
    name = request.path_params.get("name")
    if not name:
        return None
    return name if request.url.path.startswith("/api/kbs/") else None


async def _resolve_kb_name(request: Request) -> str | None:
    """The single KB this request names, for callers that genuinely need one.

    Prefers the path parameter -- the route's own identity -- over a query
    parameter, which a caller can add freely. Guards must use
    `_resolve_kb_names` and check every value instead; this exists only for
    call sites that need one name (an error message, a role lookup).
    """
    try:
        names = await _resolve_kb_names(request)
    except _UnparseableBodyError:
        return None
    return names[0] if names else None


def resolve_kb_default_role(config: PyriteConfig, db: PyriteDB, kb_name: str) -> str | None:
    """Resolve a KB's default_role from config or DB.

    Config takes precedence; falls back to DB for user-registered KBs.
    """
    kb_config = config.get_kb(kb_name)
    if kb_config and kb_config.default_role is not None:
        return kb_config.default_role
    row = db._raw_conn.execute("SELECT default_role FROM kb WHERE name = ?", (kb_name,)).fetchone()
    return row[0] if row else None


async def resolve_effective_kb_role(
    request: Request, config: PyriteConfig, db: PyriteDB, kb_name: str | None = None
) -> str | None:
    """Resolve the caller's effective role for a KB, without raising.

    Resolution chain:
    1. Global admins always pass (returns "admin")
    2. No user identity and not anonymous (an operator API key, or auth
       disabled) → global `request.state.api_role`
    3. A signed-in user or the anonymous visitor: explicit KB grant → KB
       default_role → user global role / anonymous tier

    Returns None only if no role could be determined at all (e.g. no
    `api_role` set on the request, which normally means auth failed
    upstream). Callers that need a hard 401/403 should still use
    `requires_tier`/`requires_kb_tier`; this helper is for call sites
    that need to check permissions inline without failing the request
    (e.g. deciding whether a GET is allowed to have a write side effect).

    Resolves a **single** KB name when none is given, preferring the path
    parameter. A caller that must cover every KB the request names --
    `requires_kb_tier` does -- resolves them with `_resolve_kb_names` and
    calls this once per name.
    """
    role = getattr(request.state, "api_role", None)
    if role is None:
        return None

    if role == "admin":
        return "admin"

    auth_user = getattr(request.state, "auth_user", None)
    anonymous = getattr(request.state, "anonymous", False)
    if not auth_user and not anonymous:
        # An operator API key, or auth disabled: no identity to scope by.
        return role

    if kb_name is None:
        kb_name = await _resolve_kb_name(request)
    if not kb_name:
        return role

    # A signed-in user, or the anonymous visitor (user_id None): the one
    # per-KB rule -- grant, then the KB's default_role, then the global role
    # or anonymous_tier. `readable_kbs` uses the same rule, so an anonymous
    # visitor's write check can never be looser than their read check.
    return effective_kb_role_for_user(config, db, auth_user["id"] if auth_user else None, kb_name)


def effective_kb_role_for_user(
    config: PyriteConfig, db: PyriteDB, user_id: int | None, kb_name: str, auth_service=None
) -> str | None:
    """The per-KB role rule, framework-free: grant → KB default_role → global role.

    The one implementation. `resolve_effective_kb_role` (REST's per-KB tier
    check), `kbs_for_user_at_tier` (the readable and writable sets MCP and
    `/ws` resolve per connection) all call it. `user_id=None` is the anonymous
    visitor on an auth-enabled instance.
    """
    if auth_service is None:
        from ..services.auth_service import AuthService

        auth_service = AuthService(db, config.settings.auth)
    default_role = resolve_kb_default_role(config, db, kb_name)
    return auth_service.get_kb_role(user_id, kb_name, default_role)


def kbs_for_user_at_tier(
    config: PyriteConfig,
    db: PyriteDB,
    user_id: int | None,
    role: str | None,
    tier: str,
    *,
    scoped: bool = True,
) -> set[str] | None:
    """The KBs where the caller's effective role is at least `tier`, or None
    when the caller is not scoped (a global admin, an operator API key, auth
    disabled). See `readable_kbs_for_user` for the scoping rules; this is the
    same walk at any tier, so the read and write sets cannot drift apart.
    """
    if role == "admin" or not scoped:
        return None

    from ..services.auth_service import AuthService

    auth_service = AuthService(db, config.settings.auth)
    wanted = TIER_LEVELS[tier]
    result: set[str] = set()
    for kb in config.all_kbs():
        effective = effective_kb_role_for_user(config, db, user_id, kb.name, auth_service)
        if effective is not None and TIER_LEVELS.get(effective, -1) >= wanted:
            result.add(kb.name)
    return result


def readable_kbs_for_user(
    config: PyriteConfig,
    db: PyriteDB,
    user_id: int | None,
    role: str | None,
    *,
    scoped: bool = True,
) -> set[str] | None:
    """The KBs a caller may read, or None when the caller is not scoped.

    The one rule, framework-free: no `Request`, so the MCP transport can
    apply exactly what the REST routes apply. `readable_kbs()` below is a
    thin Request-reading wrapper over it, and `mcp_routes._resolve_bearer_auth`
    is the other caller. **Do not add a second implementation** -- two copies
    drift, and a grant honoured on one surface but refused on the other is
    the bug this whole shape exists to prevent (#201).

    Not scoped (returns None): a global admin, and any caller with no user
    identity to scope by -- an operator API key, or auth disabled entirely.
    Callers that know the identity question is already settled pass
    `scoped=False` to say so.

    Scoped: `user_id` is resolved per KB through the same chain the REST
    routes use (explicit grant → KB default_role → the user's global role),
    and the KB is readable when that effective role is at least "read".
    `user_id=None` with `scoped=True` is the anonymous visitor on an
    auth-enabled instance: the same walk with no grants.
    """
    return kbs_for_user_at_tier(config, db, user_id, role, "read", scoped=scoped)


async def readable_kbs(request: Request, config: PyriteConfig, db: PyriteDB) -> set[str] | None:
    """The KBs this caller may read, or None when the caller is not scoped.

    Request-reading wrapper over `readable_kbs_for_user`: it pulls the
    identity off `request.state` and caches the answer on the request. The
    rule itself lives in the helper, shared with the MCP transport.

    Not scoped: global admins, and API-key callers (an API key is the
    operator's credential, not a peer's). A logged-in user is scoped to the KBs
    where their effective role (grant → KB default_role → global role) is at
    least read; an anonymous visitor on an auth-enabled instance is scoped the
    same way with no grants. Cached on the request.
    """
    cached = getattr(request.state, "readable_kbs", _UNSET)
    if cached is not _UNSET:
        return cached

    role = getattr(request.state, "api_role", None)
    auth_user = getattr(request.state, "auth_user", None)
    anonymous = getattr(request.state, "anonymous", False)
    result = readable_kbs_for_user(
        config,
        db,
        auth_user["id"] if auth_user else None,
        role,
        # An operator API key, or auth disabled: no user identity to scope by.
        scoped=bool(auth_user or anonymous),
    )
    request.state.readable_kbs = result
    return result


def kb_not_found(kb_name: str) -> HTTPException:
    """404 for a KB the caller may not read. Not 403: its existence is private too."""
    return HTTPException(
        status_code=404,
        detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb_name}' not found"},
    )


async def assert_kb_readable(
    request: Request, config: PyriteConfig, db: PyriteDB, kb_name: str | None
) -> None:
    """Raise 404 if kb_name is given and the caller may not read it."""
    if not kb_name:
        return
    allowed = await readable_kbs(request, config, db)
    if allowed is not None and kb_name not in allowed:
        raise kb_not_found(kb_name)


async def get_readable_kbs(
    request: Request,
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> set[str] | None:
    """Dependency form of readable_kbs() for routes that span KBs (sync or async)."""
    return await readable_kbs(request, config, db)


def requires_kb_read():
    """FastAPI dependency: **every** KB named by the request must be readable.

    Read-side counterpart of requires_kb_tier("write"). Resolves the KB from
    `kb` / `kb_name` in query, path and body -- all of them, not the first
    one found -- and 404s on any value the caller may not read. Naming a
    readable KB alongside a private one therefore buys nothing.

    Routes that span KBs (no kb given) filter with readable_kbs() instead.

    Note for the AI router: the dependency reads the request body. Starlette
    caches it on the request, so the handler's own body parsing is unaffected.
    """

    async def _check(
        request: Request,
        config: PyriteConfig = Depends(get_config),
        db: PyriteDB = Depends(get_db),
    ):
        try:
            names = await _resolve_kb_names(request)
        except _UnparseableBodyError:
            # Fail closed: an unreadable body names an unknown set of KBs,
            # and "names none" is what lets a request through.
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_BODY", "message": "Request body could not be parsed"},
            ) from None
        for name in names:
            await assert_kb_readable(request, config, db, name)

    return _check


_UNSET = object()


def kb_exists(config: PyriteConfig, db: PyriteDB, kb_name: str) -> bool:
    """Is `kb_name` a KB this instance knows -- in config or registered in the DB?"""
    if config.get_kb(kb_name):
        return True
    row = db._raw_conn.execute("SELECT 1 FROM kb WHERE name = ?", (kb_name,)).fetchone()
    return row is not None


@dataclass(frozen=True)
class RowKB:
    """What a row resolver hands `requires_kb_tier`: the KB that owns the row
    a route changes, and the 404 the route gives for a row that does not exist.

    A route whose request names no KB -- `DELETE /api/reviews/{review_id}` --
    cannot be checked against a KB it does not know. Its resolver looks the
    row up, and the per-KB rule is applied to the row's own KB. `not_found` is
    what the caller sees when that KB is unreadable, so a row in a private KB
    answers byte-for-byte like a row that does not exist.
    """

    kb_name: str
    not_found: HTTPException


async def _enforce_kb_tier(
    request: Request,
    config: PyriteConfig,
    db: PyriteDB,
    kb_name: str,
    tier: str,
    not_found: HTTPException,
) -> None:
    """The per-KB write rule for one KB.

    Passes when the caller's effective role on `kb_name` is at least `tier`.
    Otherwise: 404 (`not_found`) when the caller may not read the KB or the KB
    does not exist -- the two must answer alike, or the answer is an oracle
    for private KB names -- and 403 when the caller can read it but not
    write it.
    """
    if not kb_exists(config, db, kb_name):
        # Before the role: a missing KB must answer exactly like a private
        # one, for every caller and on every write route -- not with whatever
        # the handler behind this guard happens to say about a missing KB.
        raise not_found
    effective = await resolve_effective_kb_role(request, config, db, kb_name)
    level = TIER_LEVELS.get(effective, -1) if effective is not None else -1
    if level >= TIER_LEVELS.get(tier, 99):
        return
    if level < TIER_LEVELS["read"]:
        raise not_found
    raise HTTPException(
        status_code=403,
        detail=f"Insufficient permissions on KB '{kb_name}': requires '{tier}' tier",
    )


def requires_kb_tier(tier: str, *, resolve_kb=None):
    """FastAPI dependency factory: enforce a minimum tier on the KB(s) a write changes.

    Resolution chain, per KB:
    1. Global admins always pass
    2. Explicit KB grant → KB default_role → user global role → anonymous tier

    A KB the caller cannot read answers 404 exactly like a KB that does not
    exist; a KB the caller can read but not reach `tier` on answers 403.

    Two forms:

    - ``requires_kb_tier("write")`` -- the KB is the one the **request names**
      (`kb`/`kb_name`/... in path, query or JSON body; every value is
      checked, so naming a writable KB beside a private one buys nothing).
      A route using this form must declare a KB-bearing parameter:
      `tests/test_kb_write_guard_is_structural.py` fails otherwise, because
      a request that names no KB falls back to the caller's *global* role,
      which is never enough for a KB-scoped write.
    - ``requires_kb_tier("write", resolve_kb=dep)`` -- for a route that
      changes a row by id and names no KB. `dep` is a FastAPI dependency that
      looks the row up and returns a `RowKB`; the rule is applied to the
      row's own KB, and anything the request names is ignored.
    """
    if resolve_kb is not None:

        async def _identityless_floor(request: Request) -> None:
            """Refuse before the row is looked up when no KB could change the answer.

            A caller with no user identity -- an operator API key, or auth
            disabled -- has the same role on every KB, so a tier it lacks is
            refused here: before the resolver validates the id or reveals
            whether the row exists. A signed-in user may hold a per-KB grant,
            and an anonymous visitor a KB's default_role, above the global
            role, so for them the row's KB decides, below.
            """
            role = getattr(request.state, "api_role", None)
            if role is None:
                raise HTTPException(status_code=401, detail="Invalid or missing API key")
            identityless = not getattr(request.state, "auth_user", None) and not getattr(
                request.state, "anonymous", False
            )
            if identityless and TIER_LEVELS.get(role, -1) < TIER_LEVELS.get(tier, 99):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions: requires '{tier}' tier, your role is '{role}'",
                )

        async def _check_row_kb_tier(
            request: Request,
            # Declared first: FastAPI solves sub-dependencies in order, so the
            # floor runs before the resolver.
            _floor: None = Depends(_identityless_floor),
            row: RowKB = Depends(resolve_kb),
            config: PyriteConfig = Depends(get_config),
            db: PyriteDB = Depends(get_db),
        ):
            await _enforce_kb_tier(request, config, db, row.kb_name, tier, row.not_found)

        return _check_row_kb_tier

    async def _check_kb_tier(
        request: Request,
        config: PyriteConfig = Depends(get_config),
        db: PyriteDB = Depends(get_db),
    ):
        role = getattr(request.state, "api_role", None)
        if role is None:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

        try:
            kb_names = await _resolve_kb_names(request)
        except _UnparseableBodyError:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_BODY", "message": "Request body could not be parsed"},
            ) from None

        if not kb_names:
            # Only reachable on a route the structural test would reject: no
            # KB-bearing parameter, so the global role is all there is.
            if TIER_LEVELS.get(role, -1) < TIER_LEVELS.get(tier, 99):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions: requires '{tier}' tier, your role is '{role}'",
                )
            return

        for kb_name in kb_names:
            await _enforce_kb_tier(request, config, db, kb_name, tier, kb_not_found(kb_name))

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

    def _app_db() -> PyriteDB:
        """The app's shared ``PyriteDB`` — engine and pool, no session.

        Plain accessor for the other app-state builders below (index manager,
        KB registry, index worker), which need the object, not a request
        scope. The *dependency* is ``_app_get_db`` underneath.
        """
        if application.state.pyrite_db is None:
            cfg = application.state.pyrite_config
            db = PyriteDB(cfg.settings.index_path)
            application.state.pyrite_db = db
            db.merge_registered_kbs(cfg)
        return application.state.pyrite_db

    def _app_get_db():
        """Per-request database session (#131).

        The ``PyriteDB`` — and so the engine and its connection pool — is still
        built once and cached on app state; what is now per-request is the
        SQLAlchemy ``Session``. ``session_scope()`` binds a fresh one for the
        duration of this request and closes it in its ``finally``, on every
        path including exceptions.

        Being a generator dependency, FastAPI opens the handle before the
        handler and closes it after the response is produced. The handler
        receives a per-request *handle* onto the same database — same engine,
        pool, raw connection and backend — whose ``db.session`` and backend
        ``self._session`` resolve to this request's own Session. That is why no
        service or endpoint signature had to change.

        The handle, rather than a thread-local or a ContextVar, is what makes
        this correct: one anyio worker thread interleaves several requests (see
        ``PyriteDB.session`` for the measurements), so neither the thread nor
        the context identifies a request.

        Both halves of the fix are required and both are here: the per-request
        session (isolation) and its close (returning the connection to the
        pool, which ``storage/connection.py`` sizes to the anyio threadpool so
        the close cannot be traded for ``QueuePool limit ... reached``).
        """
        db = _app_db()
        with db.request_handle() as handle:
            yield handle

    def _app_get_index_mgr() -> IndexManager:
        if application.state.pyrite_index_mgr is None:
            application.state.pyrite_index_mgr = IndexManager(_app_db(), _app_get_config())
        return application.state.pyrite_index_mgr

    def _app_get_kb_registry() -> KBRegistryService:
        """The startup/seeding registry, bound to the shared ``PyriteDB``.

        Not a request dependency -- see ``_request_kb_registry`` below. This
        one exists for ``seed_from_config()`` at startup, where there is no
        request and so no per-request session to bind to.
        """
        if application.state.pyrite_kb_registry is None:
            application.state.pyrite_kb_registry = KBRegistryService(
                _app_get_config(), _app_db(), _app_get_index_mgr()
            )
        return application.state.pyrite_kb_registry

    def _request_kb_registry(db: PyriteDB = Depends(_app_get_db)) -> KBRegistryService:
        """A registry bound to *this request's* handle.

        The cached app-state registry holds the shared ``PyriteDB``, so its
        ORM reads resolve to the thread-local fallback session -- which opens
        a transaction per request that nothing closes, and the connection is
        never returned to the pool. Measured before this: five requests to
        ``GET /api/kbs`` produced five checkouts and zero check-ins, and
        request 58 died with ``QueuePool limit of size 40 overflow 20
        reached``. Building it per request from the handle costs one object
        and keeps the engine, pool and backend shared.
        """
        return KBRegistryService(_app_get_config(), db, _app_get_index_mgr())

    def _app_get_index_worker() -> IndexWorker:
        if application.state.pyrite_index_worker is None:
            worker = IndexWorker(_app_db(), _app_get_config())

            # Wire WebSocket broadcast for progress updates. The callback runs
            # on an IndexWorker thread; broadcast_event hands it to the loop
            # captured at startup (#322). index_progress is operator
            # information and reaches unscoped sockets only, whatever the
            # job's KB (UNSCOPED_ONLY_EVENTS); kb_name is carried for them.
            def _ws_progress(job_id: str, current: int, total: int, kb_name: str | None):
                from .websocket import broadcast_event

                broadcast_event(
                    "index_progress",
                    job_id=job_id,
                    current=current,
                    total=total,
                    kb_name=kb_name,
                )

            worker.on_progress = _ws_progress
            application.state.pyrite_index_worker = worker
        return application.state.pyrite_index_worker

    application.dependency_overrides[get_config] = _app_get_config
    application.dependency_overrides[get_db] = _app_get_db
    application.dependency_overrides[get_index_mgr] = _app_get_index_mgr
    application.dependency_overrides[get_index_worker] = _app_get_index_worker
    application.dependency_overrides[get_kb_registry] = _request_kb_registry

    # Seed config KBs into DB registry
    try:
        registry = _app_get_kb_registry()
        seeded = registry.seed_from_config()
        if seeded:
            logger.info("Seeded %d config KB(s) into registry", seeded)
    except Exception:
        logger.warning("Failed to seed KB registry from config", exc_info=True)

    # Set up embedding service for prewarm and actually pre-warm it on startup.
    # This used to only construct the EmbeddingService and stop -- the comment
    # said "actual prewarm happens in lifespan" but no lifespan/startup hook
    # ever called .prewarm(), so /health's embeddings.ready stayed false
    # forever and the first real search/embed request always paid the full
    # cold-start cost this feature exists to avoid. Runs in a thread since
    # prewarm() is a blocking sentence-transformers model load.
    if config.settings.prewarm_embeddings:
        from ..services.embedding_service import EmbeddingService

        application.state.pyrite_embedding_svc = EmbeddingService(
            _app_db(), model_name=config.settings.embedding_model
        )

        @application.on_event("startup")
        async def _prewarm_embedding_model() -> None:
            from starlette.concurrency import run_in_threadpool

            warmed = await run_in_threadpool(application.state.pyrite_embedding_svc.prewarm)
            if warmed:
                logger.info("Embedding model pre-warmed on startup")
            else:
                logger.warning(
                    "Embedding model pre-warm failed or unavailable "
                    "(sentence-transformers not installed?)"
                )

    # ADR-0035: writes enqueue rather than embed, so anything written while
    # this process -- or a previous one -- had no model is sitting in
    # embed_queue. Draining it is what turns "eventually embedded" into
    # "embedded".
    #
    # **Deliberately outside the `prewarm_embeddings` branch above.** That
    # setting defaults to False, so gating the drain on it meant the default
    # server (`auto_embed: true`, `prewarm_embeddings: false`) enqueued
    # forever with only the admin-tier `POST /api/index/sync?wait=true` left
    # to drain it -- every `--mode semantic` returning [] on a stock install,
    # a straight functional loss against the synchronous behaviour ADR-0035
    # replaced. Affordable unconditionally because `settle_embed_queue`
    # checks `has_pending()` first: one indexed COUNT, and no EmbeddingService
    # (so no torch) when there is nothing owed, which is the usual case.
    #
    # Still no background thread (#102): this runs in the startup threadpool,
    # which the server already waits on before serving.
    @application.on_event("startup")
    async def _drain_embed_queue_on_startup() -> None:
        from starlette.concurrency import run_in_threadpool

        # `_app_db()`, not the `_app_get_db` dependency: this runs at startup,
        # outside any request, and the dependency is a generator FastAPI is
        # meant to open and close around a handler. Calling it directly returns
        # the generator object itself, and the first attribute access on it
        # fails with `'generator' object has no attribute '_raw_conn'`, so the
        # drain never runs and a stock install embeds nothing.
        db = _app_db()
        await run_in_threadpool(lambda: _drain_embed_queue(db, label="startup"))

    # Sync routes and IndexWorker threads have no running loop; they hand
    # WebSocket events to this one (#326, #322). Captured here, not at import,
    # because the loop that serves the sockets exists only once the server
    # starts; released at shutdown so a later app in the same process (the
    # manager is module-global) never hands events to a dead loop.
    # Pinned by tests/test_websocket_delivery.py (TestLoopLifetime, TestBindUnbind).
    @application.on_event("startup")
    async def _bind_websocket_loop() -> None:
        import asyncio

        from .websocket import bind_loop

        application.state.pyrite_ws_loop = asyncio.get_running_loop()
        bind_loop(application.state.pyrite_ws_loop)

    # A socket lives no longer than the credential that opened it (#411,
    # ADR-0036): AuthService announces each session end or scope change and
    # the socket manager closes the sockets it names. Subscribing is
    # idempotent and never undone -- the listener is module-level, like the
    # manager, and does nothing while no live loop is bound. The expiry sweep
    # lives exactly as long as this app's loop.
    # Pinned by tests/test_websocket_credential_lifetime.py.
    @application.on_event("startup")
    async def _start_socket_credential_lifetime() -> None:
        import asyncio

        from ..services import credential_events
        from .websocket import expiry_sweep, on_credential_change

        credential_events.subscribe(on_credential_change)
        application.state.pyrite_ws_expiry_sweep = asyncio.get_running_loop().create_task(
            expiry_sweep()
        )

    @application.on_event("shutdown")
    async def _unbind_websocket_loop() -> None:
        import asyncio

        from .websocket import unbind_loop

        sweep = getattr(application.state, "pyrite_ws_expiry_sweep", None)
        if sweep is not None:
            sweep.cancel()
            # Bounded: shutdown never waits on the sweep for long.
            await asyncio.wait({sweep}, timeout=5)
        unbind_loop(application.state.pyrite_ws_loop)

    # CORS — use configured origins; disable credentials with wildcard (spec compliance)
    origins = config.settings.cors_origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Host allow-list and cross-origin write refusal for the credential-free
    # (auth disabled) mode. Added after CORS so it is the outermost layer: a
    # request to an unexpected Host is refused before anything else runs.
    from .request_guard import RequestGuardMiddleware

    application.add_middleware(RequestGuardMiddleware, get_config=_app_get_config)

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

    # Central handler for the domain exception hierarchy (see
    # register_pyrite_exception_handler): any uncaught PyriteError is mapped to
    # a proper HTTP status + uniform {"code","message"} body instead of a 500.
    register_pyrite_exception_handler(application)

    # Auth router (mounted outside /api, no verify_api_key dependency)
    from .auth_endpoints import auth_router

    application.include_router(auth_router)

    # Branding router (public — the login page needs it before auth)
    from .branding_endpoints import branding_router

    application.include_router(branding_router)

    # SEO endpoints: sitemap.xml + robots.txt (public — crawlers don't auth)
    from .seo_endpoints import seo_router

    application.include_router(seo_router)

    # MCP SSE transport (mounted outside /api — handles its own Bearer auth)
    from .mcp_routes import mount_mcp_routes

    # The shared PyriteDB, not the `_app_get_db` generator dependency: the MCP
    # routes are plain Starlette handlers, so no DI runs the generator; they
    # open their own per-request handle (#131) around the auth lookup.
    mount_mcp_routes(application, _app_get_config, _app_db)

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
        """Authenticate the handshake, then register the socket with its scope.

        Rejected handshakes are closed *before* ``accept`` and never reach the
        manager (#218). The readable set is fixed for the connection's life,
        and the connection lives no longer than its credential (ADR-0036).
        The resolution runs on a worker thread with its own short-lived DB
        handle -- not a ``Depends(get_db)`` session, which would stay open for
        as long as the socket does.
        """
        from starlette.concurrency import run_in_threadpool

        from .websocket import HandshakeRejectedError, manager, origin_allowed, resolve_socket_scope

        cfg = application.state.pyrite_config
        if not origin_allowed(ws, cfg):
            # Logged: behind a proxy that rewrites Host, this is the only
            # trace of why the web UI's socket never connects.
            logger.warning(
                "Refused /ws handshake: Origin %r is neither this server's Host %r "
                "nor listed in cors_origins",
                ws.headers.get("origin"),
                ws.headers.get("host"),
            )
            await ws.close(code=1008)
            return

        def _resolve():
            with _app_db().request_handle() as db:
                return resolve_socket_scope(ws, cfg, db)

        # Read before resolving: a credential change processed after this
        # point may have revoked what `_resolve` is about to find valid.
        epoch = manager.epoch
        try:
            scope = await run_in_threadpool(_resolve)
        except HandshakeRejectedError:
            logger.info("Refused /ws handshake: no credential admits this socket")
            await ws.close(code=1008)
            return

        if not await manager.connect(ws, scope, epoch):
            return
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
