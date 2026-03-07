"""
Auth endpoints for web UI authentication.

Mounted at /auth (outside /api) to bypass API key verification.
Provides register, login, logout, session introspection, and OAuth flows.
"""

import logging
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..config import PyriteConfig
from ..services.auth_service import AuthService
from ..services.oauth_providers import GitHubOAuthProvider
from ..storage.database import PyriteDB
from .api import get_config, get_db

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

_auth_service: AuthService | None = None


def get_auth_service(
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
) -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(db, config.settings.auth)
    elif _auth_service.db is not db:
        _auth_service = AuthService(db, config.settings.auth)
    return _auth_service


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthUserResponse(BaseModel):
    id: int
    username: str
    display_name: str | None
    role: str
    auth_provider: str = "local"
    avatar_url: str | None = None
    kb_permissions: dict[str, str] = {}


class AuthConfigResponse(BaseModel):
    enabled: bool
    allow_registration: bool
    providers: list[str] = []


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

COOKIE_NAME = "pyrite_session"


def _set_session_cookie(response: Response, token: str, ttl_hours: int, request: Request) -> None:
    secure = request.url.scheme == "https"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
        max_age=ttl_hours * 3600,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


# ---------------------------------------------------------------------------
# CSRF state store (in-memory, single-process — fine for Phase 1)
# ---------------------------------------------------------------------------

_oauth_states: dict[str, float] = {}  # {state: expiry_timestamp}
_OAUTH_STATE_TTL = 300  # 5 minutes


def _create_oauth_state() -> str:
    """Generate a CSRF state token and store it."""
    # Probabilistic cleanup (1 in 10 calls)
    if secrets.randbelow(10) == 0:
        now = time.time()
        expired = [k for k, v in _oauth_states.items() if v < now]
        for k in expired:
            del _oauth_states[k]

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = time.time() + _OAUTH_STATE_TTL
    return state


def _verify_oauth_state(state: str) -> bool:
    """Verify and consume a CSRF state token."""
    expiry = _oauth_states.pop(state, None)
    if expiry is None:
        return False
    return time.time() < expiry


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@auth_router.get("/users")
async def list_users(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """List all users. Requires admin role."""
    auth_user = getattr(request.state, "auth_user", None)
    global_role = getattr(request.state, "api_role", None)

    is_admin = global_role == "admin" or (auth_user and auth_user.get("role") == "admin")
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return {"users": auth_service.list_users()}


@auth_router.get("/config")
async def get_auth_config(
    config: PyriteConfig = Depends(get_config),
) -> AuthConfigResponse:
    """Public endpoint: returns auth configuration for the frontend."""
    providers = [name for name, p in config.settings.auth.providers.items() if p.client_id]
    return AuthConfigResponse(
        enabled=config.settings.auth.enabled,
        allow_registration=config.settings.auth.allow_registration,
        providers=providers,
    )


@auth_router.post("/register")
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    config: PyriteConfig = Depends(get_config),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthUserResponse:
    """Create a new account. First user gets admin role."""
    if not config.settings.auth.enabled:
        raise HTTPException(status_code=400, detail="Authentication is not enabled")

    try:
        user = auth_service.register(body.username, body.password, body.display_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Auto-login after registration
    _, token = auth_service.login(body.username, body.password)
    _set_session_cookie(response, token, config.settings.auth.session_ttl_hours, request)

    return AuthUserResponse(**user)


@auth_router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    config: PyriteConfig = Depends(get_config),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthUserResponse:
    """Authenticate and set session cookie."""
    if not config.settings.auth.enabled:
        raise HTTPException(status_code=400, detail="Authentication is not enabled")

    try:
        user, token = auth_service.login(body.username, body.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    _set_session_cookie(response, token, config.settings.auth.session_ttl_hours, request)
    return AuthUserResponse(**user)


@auth_router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Clear session cookie and delete server-side session."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        auth_service.logout(token)
    _clear_session_cookie(response)
    return {"ok": True}


@auth_router.get("/me")
async def get_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthUserResponse:
    """Return current user from session cookie, or 401."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = auth_service.verify_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Include per-KB permissions
    kb_perms = auth_service.get_user_kb_permissions(user["id"])
    user["kb_permissions"] = kb_perms

    return AuthUserResponse(**user)


# ---------------------------------------------------------------------------
# GitHub OAuth endpoints
# ---------------------------------------------------------------------------


@auth_router.get("/github")
async def github_oauth_start(
    request: Request,
    config: PyriteConfig = Depends(get_config),
) -> RedirectResponse:
    """Redirect user to GitHub for authorization."""
    gh_config = config.settings.auth.providers.get("github")
    if not gh_config or not gh_config.client_id:
        raise HTTPException(status_code=404, detail="GitHub OAuth is not configured")

    provider = GitHubOAuthProvider(gh_config.client_id, gh_config.client_secret)
    state = _create_oauth_state()

    # Build callback URL from request
    callback_url = str(request.url_for("github_oauth_callback"))
    authorize_url = provider.get_authorize_url(callback_url, state)

    return RedirectResponse(url=authorize_url, status_code=302)


@auth_router.get("/github/callback")
async def github_oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    config: PyriteConfig = Depends(get_config),
    auth_service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Handle GitHub OAuth callback."""
    if error or not code:
        logger.warning("GitHub OAuth error: %s", error or "no code")
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)

    if not _verify_oauth_state(state):
        logger.warning("GitHub OAuth invalid/expired state")
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)

    gh_config = config.settings.auth.providers.get("github")
    if not gh_config or not gh_config.client_id:
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)

    provider = GitHubOAuthProvider(gh_config.client_id, gh_config.client_secret)
    callback_url = str(request.url_for("github_oauth_callback"))

    try:
        token = await provider.exchange_code(code, callback_url)
        profile = await provider.get_user_profile(token)
        user, session_token = auth_service.oauth_login(profile, gh_config)
    except ValueError as e:
        logger.warning("GitHub OAuth login failed: %s", e)
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)
    except Exception:
        logger.exception("GitHub OAuth unexpected error")
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)

    response = RedirectResponse(url="/", status_code=302)
    _set_session_cookie(response, session_token, config.settings.auth.session_ttl_hours, request)
    return response
