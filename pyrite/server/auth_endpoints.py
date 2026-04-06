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
    invite_code: str | None = None


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
    require_invite_code: bool = False
    providers: list[str] = []
    anonymous_tier: str = "none"


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

_oauth_states: dict[str, dict] = {}  # {state: {"expiry": float, "flow": str, "user_id": int|None}}
_OAUTH_STATE_TTL = 300  # 5 minutes


def _create_oauth_state(flow: str = "login", user_id: int | None = None) -> str:
    """Generate a CSRF state token and store it with flow metadata."""
    # Probabilistic cleanup (1 in 10 calls)
    if secrets.randbelow(10) == 0:
        now = time.time()
        expired = [k for k, v in _oauth_states.items() if v["expiry"] < now]
        for k in expired:
            del _oauth_states[k]

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "expiry": time.time() + _OAUTH_STATE_TTL,
        "flow": flow,
        "user_id": user_id,
    }
    return state


def _verify_oauth_state(state: str) -> dict | None:
    """Verify and consume a CSRF state token. Returns state metadata or None."""
    state_data = _oauth_states.pop(state, None)
    if state_data is None:
        return None
    if time.time() >= state_data["expiry"]:
        return None
    return state_data


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


@auth_router.put("/users/{user_id}/role")
async def set_user_role(
    request: Request,
    user_id: int,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Update a user's global role. Requires admin."""
    auth_user = getattr(request.state, "auth_user", None)
    global_role = getattr(request.state, "api_role", None)
    is_admin = global_role == "admin" or (auth_user and auth_user.get("role") == "admin")
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    body = await request.json()
    role = body.get("role", "")
    if role not in ("read", "write", "admin"):
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    found = auth_service.set_role(user_id, role)
    if not found:
        raise HTTPException(status_code=404, detail="User not found")
    return {"updated": True, "user_id": user_id, "role": role}


@auth_router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    request: Request,
    user_id: int,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Get a user's per-KB permissions. Requires admin."""
    auth_user = getattr(request.state, "auth_user", None)
    global_role = getattr(request.state, "api_role", None)
    is_admin = global_role == "admin" or (auth_user and auth_user.get("role") == "admin")
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    perms = auth_service.get_user_kb_permissions(user_id)
    return {"user_id": user_id, "permissions": perms}


@auth_router.get("/config")
async def get_auth_config(
    config: PyriteConfig = Depends(get_config),
) -> AuthConfigResponse:
    """Public endpoint: returns auth configuration for the frontend."""
    providers = [name for name, p in config.settings.auth.providers.items() if p.client_id]
    return AuthConfigResponse(
        enabled=config.settings.auth.enabled,
        allow_registration=config.settings.auth.allow_registration,
        require_invite_code=config.settings.auth.require_invite_code,
        providers=providers,
        anonymous_tier=config.settings.auth.anonymous_tier or "none",
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
        user = auth_service.register(body.username, body.password, body.display_name, body.invite_code)
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

    state_data = _verify_oauth_state(state)
    if not state_data:
        logger.warning("GitHub OAuth invalid/expired state")
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)

    gh_config = config.settings.auth.providers.get("github")
    if not gh_config or not gh_config.client_id:
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)

    provider = GitHubOAuthProvider(gh_config.client_id, gh_config.client_secret)
    callback_url = str(request.url_for("github_oauth_callback"))

    try:
        token = await provider.exchange_code(code, callback_url)
    except ValueError as e:
        logger.warning("GitHub OAuth token exchange failed: %s", e)
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)
    except Exception:
        logger.exception("GitHub OAuth unexpected error during token exchange")
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)

    # Handle "connect" flow — store token for existing user, don't create session
    if state_data.get("flow") == "connect":
        connect_user_id = state_data.get("user_id")
        if not connect_user_id:
            return RedirectResponse(url="/settings/kbs?error=connect_failed", status_code=302)
        try:
            auth_service.store_github_token(connect_user_id, token.access_token, token.scope)
            return RedirectResponse(url="/settings/kbs?github=connected", status_code=302)
        except Exception:
            logger.exception("Failed to store GitHub token")
            return RedirectResponse(url="/settings/kbs?error=connect_failed", status_code=302)

    # Standard login flow
    try:
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


# ---------------------------------------------------------------------------
# GitHub Connect (scope escalation for repo access)
# ---------------------------------------------------------------------------

CONNECT_SCOPES = "read:user read:org public_repo"


@auth_router.get("/github/connect")
async def github_connect_start(
    request: Request,
    config: PyriteConfig = Depends(get_config),
    auth_service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Redirect logged-in user to GitHub with public_repo scope for repo operations."""
    gh_config = config.settings.auth.providers.get("github")
    if not gh_config or not gh_config.client_id:
        raise HTTPException(status_code=404, detail="GitHub OAuth is not configured")

    # Require authenticated user
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = auth_service.verify_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")

    provider = GitHubOAuthProvider(gh_config.client_id, gh_config.client_secret)
    state = _create_oauth_state(flow="connect", user_id=user["id"])

    callback_url = str(request.url_for("github_oauth_callback"))
    # Build authorize URL with elevated scopes
    from urllib.parse import urlencode

    params = {
        "client_id": gh_config.client_id,
        "redirect_uri": callback_url,
        "scope": CONNECT_SCOPES,
        "state": state,
    }
    authorize_url = f"{provider.AUTHORIZE_URL}?{urlencode(params)}"

    return RedirectResponse(url=authorize_url, status_code=302)


@auth_router.get("/github/status")
async def github_connection_status(
    request: Request,
    config: PyriteConfig = Depends(get_config),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Check if current user has a connected GitHub token."""
    gh_config = config.settings.auth.providers.get("github")
    if not gh_config or not gh_config.client_id:
        return {"connected": False, "github_configured": False}

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return {"connected": False, "github_configured": True}

    user = auth_service.verify_session(token)
    if not user:
        return {"connected": False, "github_configured": True}

    gh_token, scopes = auth_service.get_github_token_for_user(user["id"])
    if not gh_token:
        return {"connected": False, "github_configured": True}

    # Optionally verify token is still valid
    username = None
    try:
        from ..github_auth import get_github_user_info

        info = get_github_user_info(gh_token)
        if info:
            username = info.get("login")
        else:
            # Token invalid, clear it
            auth_service.clear_github_token(user["id"])
            return {"connected": False, "github_configured": True, "reason": "token_expired"}
    except Exception:
        pass

    return {
        "connected": True,
        "github_configured": True,
        "username": username,
        "scopes": scopes,
    }


@auth_router.delete("/github/connect")
async def github_disconnect(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Disconnect GitHub by removing stored token."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = auth_service.verify_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")

    auth_service.clear_github_token(user["id"])
    return {"ok": True, "message": "GitHub disconnected"}


def _require_auth(request: Request) -> dict:
    """Extract authenticated user from request or raise 401."""
    user = getattr(request.state, "auth_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


# ── User API Key Management (BYOK) ────────────────────────────────────


class StoreApiKeyRequest(BaseModel):
    provider: str  # anthropic, openai, gemini, openrouter
    api_key: str
    model: str = ""


def _require_session_auth(request: Request, auth_service: AuthService) -> dict:
    """Authenticate via session cookie and return user dict, or raise 401."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = auth_service.verify_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return user


@auth_router.get("/api-keys")
async def list_user_api_keys(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """List the current user's configured LLM providers (no keys exposed)."""
    user = _require_session_auth(request, auth_service)
    keys = auth_service.list_user_api_keys(user["id"])
    return {"keys": keys}


@auth_router.post("/api-keys")
async def store_user_api_key(
    body: StoreApiKeyRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Store or update the current user's API key for a provider."""
    user = _require_session_auth(request, auth_service)
    valid_providers = ("anthropic", "openai", "gemini", "openrouter", "ollama")
    if body.provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {body.provider}. Must be one of: {', '.join(valid_providers)}",
        )
    result = auth_service.store_user_api_key(user["id"], body.provider, body.api_key, body.model)
    return result


@auth_router.delete("/api-keys/{provider}")
async def delete_user_api_key(
    provider: str,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Delete the current user's API key for a provider."""
    user = _require_session_auth(request, auth_service)
    deleted = auth_service.delete_user_api_key(user["id"], provider)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No API key found for provider: {provider}")
    return {"ok": True, "provider": provider}


# ── Invite Code Management (admin only) ────────────────────────────────


class CreateInviteRequest(BaseModel):
    role: str = "write"
    note: str = ""
    expires_hours: int | None = None


@auth_router.post("/invite-codes")
async def create_invite_code(
    body: CreateInviteRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Create a new invite code (admin only)."""
    user = _require_auth(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return auth_service.create_invite_code(
        created_by=user["username"],
        role=body.role,
        note=body.note,
        expires_hours=body.expires_hours,
    )


@auth_router.get("/invite-codes")
async def list_invite_codes(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """List all invite codes (admin only)."""
    user = _require_auth(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"codes": auth_service.list_invite_codes()}


@auth_router.delete("/invite-codes/{code}")
async def delete_invite_code(
    code: str,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Delete an unused invite code (admin only)."""
    user = _require_auth(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        auth_service.delete_invite_code(code)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
