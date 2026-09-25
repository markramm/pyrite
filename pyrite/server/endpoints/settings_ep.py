"""Settings endpoints.

Settings are instance-wide. Most are UI preferences any write-tier caller
may change; **operator settings** -- the AI provider family, and any key
holding a credential -- change what the server does on the operator's
behalf, so they require the admin tier. **Secret settings** (credentials)
are never returned by any read, to anyone: the read carries ``MASK`` in
their place and lists them under ``masked``. A URL setting (``ai.baseUrl``)
is returned to non-admins with any embedded credential masked. The server itself reads the
real value straight from the database (``get_llm_service``).
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Request

from ...services.settings_service import SettingsService
from ..api import (
    TIER_LEVELS,
    get_settings_service,
    invalidate_llm_service,
    limiter,
    requires_tier,
)
from ..schemas import (
    BulkSettingsUpdateRequest,
    SettingResponse,
    SettingsResponse,
    SettingUpdateRequest,
)

router = APIRouter(tags=["Settings"])

# Settings keys that require LLM service invalidation on change
_AI_SETTINGS_PREFIXES = ("ai.",)

# Operator settings: the whole AI provider family. Not only the key --
# pointing `ai.baseUrl` at another host would send the operator's key there.
_OPERATOR_PREFIXES = ("ai.",)

# The settings known to hold a credential. Add to this when a new one is
# introduced; the name heuristic below is only the fallback for a key nobody
# listed.
SECRET_SETTINGS: frozenset[str] = frozenset({"ai.apiKey"})

# A key whose final segment names a credential is secret wherever it lives.
_SECRET_MARKERS = ("apikey", "api_key", "token", "secret", "password", "credential")

# Settings holding a URL that may embed a credential (userinfo, or a key in
# the query string). Non-admins get the URL with those parts masked.
_URL_SETTINGS: frozenset[str] = frozenset({"ai.baseUrl"})

# Query parameter names that carry a credential, compared lowercased with
# `-` and `_` removed.
_CREDENTIAL_PARAMS = (
    "key",
    "apikey",
    "token",
    "accesstoken",
    "secret",
    "password",
    "sig",
    "signature",
    "auth",
    "code",
)

# What a read shows in place of a secret that is set. Writing it back is a
# no-op, so a client that saves every field it loaded keeps the real value.
MASK = "********"


def is_secret_setting(key: str) -> bool:
    """True when the key holds a credential: listed in ``SECRET_SETTINGS``,
    or (fallback) its final segment names one."""
    if key in SECRET_SETTINGS:
        return True
    leaf = key.rsplit(".", 1)[-1].lower()
    return any(marker in leaf for marker in _SECRET_MARKERS)


def is_operator_setting(key: str) -> bool:
    """True when changing the key requires the admin tier."""
    return key.startswith(_OPERATOR_PREFIXES) or is_secret_setting(key)


def _require_admin_for(request: Request, keys) -> None:
    operator_keys = sorted(k for k in keys if is_operator_setting(k))
    if not operator_keys:
        return
    if not _is_admin(request):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ADMIN_REQUIRED",
                "message": f"Changing operator settings requires the admin tier: {operator_keys}",
            },
        )


def _is_credential_param(name: str) -> bool:
    norm = name.lower().replace("-", "").replace("_", "")
    return norm in _CREDENTIAL_PARAMS or norm.endswith(("key", "token", "secret"))


def redact_url_credentials(url: str) -> str:
    """The URL with any userinfo and credential-bearing query values masked.

    Scheme, host, port, path and ordinary query parameters are kept, so the
    setting still says which endpoint is configured. A value that cannot be
    parsed as a URL is masked whole.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return MASK
    netloc = parts.netloc
    if "@" in netloc:
        netloc = f"{MASK}@{netloc.rsplit('@', 1)[1]}"
    query = parts.query
    if query:
        pairs = parse_qsl(query, keep_blank_values=True)
        query = urlencode([(k, MASK if _is_credential_param(k) else v) for k, v in pairs], safe="*")
    return urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment))


def _is_admin(request: Request) -> bool:
    role = getattr(request.state, "api_role", None)
    return TIER_LEVELS.get(role, -1) >= TIER_LEVELS["admin"]


def _masked_value(key: str, value: str | None, *, admin: bool) -> str | None:
    if value is None:
        return None
    if is_secret_setting(key):
        return MASK
    if key in _URL_SETTINGS and not admin:
        return redact_url_credentials(value)
    return value


def _masked_settings(settings: dict[str, str], *, admin: bool) -> SettingsResponse:
    return SettingsResponse(
        settings={k: _masked_value(k, v, admin=admin) for k, v in settings.items()},
        masked=sorted(k for k in settings if is_secret_setting(k)),
    )


def _maybe_invalidate_llm(key: str) -> None:
    """Invalidate cached LLM service if an AI setting changed."""
    if any(key.startswith(p) for p in _AI_SETTINGS_PREFIXES):
        invalidate_llm_service()


def _write(settings: SettingsService, key: str, value: str) -> None:
    if is_secret_setting(key) and value == MASK:
        return  # the mask read back unchanged: keep the stored secret
    settings.set(key, value)
    _maybe_invalidate_llm(key)


@router.get("/settings", response_model=SettingsResponse)
@limiter.limit("100/minute")
def get_all_settings(
    request: Request,
    settings: SettingsService = Depends(get_settings_service),
):
    """Get all settings (secret values masked)."""
    return _masked_settings(settings.all(), admin=_is_admin(request))


@router.put("/settings", dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def bulk_update_settings(
    request: Request,
    req: BulkSettingsUpdateRequest,
    settings: SettingsService = Depends(get_settings_service),
):
    """Bulk update settings. All-or-nothing on the admin check."""
    _require_admin_for(request, req.settings.keys())
    for key, value in req.settings.items():
        _write(settings, key, value)
    return _masked_settings(settings.all(), admin=_is_admin(request))


@router.get("/settings/{key}", response_model=SettingResponse)
@limiter.limit("100/minute")
def get_setting(
    request: Request,
    key: str,
    settings: SettingsService = Depends(get_settings_service),
):
    """Get a single setting (a secret value is masked)."""
    value = _masked_value(key, settings.get(key), admin=_is_admin(request))
    return SettingResponse(key=key, value=value)


@router.put(
    "/settings/{key}",
    response_model=SettingResponse,
    dependencies=[Depends(requires_tier("write"))],
)
@limiter.limit("30/minute")
def set_setting(
    request: Request,
    key: str,
    req: SettingUpdateRequest,
    settings: SettingsService = Depends(get_settings_service),
):
    """Set a single setting."""
    _require_admin_for(request, [key])
    _write(settings, key, req.value)
    value = _masked_value(key, settings.get(key), admin=_is_admin(request))
    return SettingResponse(key=key, value=value)


@router.delete("/settings/{key}", dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def delete_setting(
    request: Request,
    key: str,
    settings: SettingsService = Depends(get_settings_service),
):
    """Delete a setting."""
    _require_admin_for(request, [key])
    deleted = settings.delete(key)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Setting '{key}' not found"},
        )
    _maybe_invalidate_llm(key)
    return {"deleted": True, "key": key}
