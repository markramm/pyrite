"""
Auth endpoints for web UI authentication.

Mounted at /auth (outside /api) to bypass API key verification.
Provides register, login, logout, and session introspection.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ..config import PyriteConfig
from ..services.auth_service import AuthService
from ..storage.database import PyriteDB
from .api import get_config, get_db

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


class AuthConfigResponse(BaseModel):
    enabled: bool
    allow_registration: bool


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

COOKIE_NAME = "pyrite_session"


def _set_session_cookie(
    response: Response, token: str, ttl_hours: int, request: Request
) -> None:
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
# Endpoints
# ---------------------------------------------------------------------------


@auth_router.get("/config")
async def get_auth_config(
    config: PyriteConfig = Depends(get_config),
) -> AuthConfigResponse:
    """Public endpoint: returns auth configuration for the frontend."""
    return AuthConfigResponse(
        enabled=config.settings.auth.enabled,
        allow_registration=config.settings.auth.allow_registration,
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
        user = auth_service.register(
            body.username, body.password, body.display_name
        )
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

    return AuthUserResponse(**user)
