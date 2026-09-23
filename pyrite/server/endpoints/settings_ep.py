"""Settings endpoints.

Settings are instance-wide. Most are UI preferences any write-tier caller
may change; **operator settings** -- the AI provider family, and any key
holding a credential -- change what the server does on the operator's
behalf, so they require the admin tier. **Secret settings** (credentials)
are never returned by any read, to anyone: the read carries ``MASK`` in
their place and lists them under ``masked``. The server itself reads the
real value straight from the database (``get_llm_service``).
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from ...services.kb_service import KBService
from ..api import TIER_LEVELS, get_kb_service, invalidate_llm_service, limiter, requires_tier
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

# A key whose final segment names a credential is secret wherever it lives.
_SECRET_MARKERS = ("apikey", "api_key", "token", "secret", "password", "credential")

# What a read shows in place of a secret that is set. Writing it back is a
# no-op, so a client that saves every field it loaded keeps the real value.
MASK = "********"


def is_secret_setting(key: str) -> bool:
    """True when the key holds a credential (e.g. ``ai.apiKey``)."""
    leaf = key.rsplit(".", 1)[-1].lower()
    return any(marker in leaf for marker in _SECRET_MARKERS)


def is_operator_setting(key: str) -> bool:
    """True when changing the key requires the admin tier."""
    return key.startswith(_OPERATOR_PREFIXES) or is_secret_setting(key)


def _require_admin_for(request: Request, keys) -> None:
    operator_keys = sorted(k for k in keys if is_operator_setting(k))
    if not operator_keys:
        return
    role = getattr(request.state, "api_role", None)
    if TIER_LEVELS.get(role, -1) < TIER_LEVELS["admin"]:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ADMIN_REQUIRED",
                "message": f"Changing operator settings requires the admin tier: {operator_keys}",
            },
        )


def _masked_value(key: str, value: str | None) -> str | None:
    if value is not None and is_secret_setting(key):
        return MASK
    return value


def _masked_settings(settings: dict[str, str]) -> SettingsResponse:
    return SettingsResponse(
        settings={k: _masked_value(k, v) for k, v in settings.items()},
        masked=sorted(k for k in settings if is_secret_setting(k)),
    )


def _maybe_invalidate_llm(key: str) -> None:
    """Invalidate cached LLM service if an AI setting changed."""
    if any(key.startswith(p) for p in _AI_SETTINGS_PREFIXES):
        invalidate_llm_service()


def _write(svc: KBService, key: str, value: str) -> None:
    if is_secret_setting(key) and value == MASK:
        return  # the mask read back unchanged: keep the stored secret
    svc.db.set_setting(key, value)
    _maybe_invalidate_llm(key)


@router.get("/settings", response_model=SettingsResponse)
@limiter.limit("100/minute")
def get_all_settings(
    request: Request,
    svc: KBService = Depends(get_kb_service),
):
    """Get all settings (secret values masked)."""
    return _masked_settings(svc.db.get_all_settings())


@router.put("/settings", dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def bulk_update_settings(
    request: Request,
    req: BulkSettingsUpdateRequest,
    svc: KBService = Depends(get_kb_service),
):
    """Bulk update settings. All-or-nothing on the admin check."""
    _require_admin_for(request, req.settings.keys())
    for key, value in req.settings.items():
        _write(svc, key, value)
    return _masked_settings(svc.db.get_all_settings())


@router.get("/settings/{key}", response_model=SettingResponse)
@limiter.limit("100/minute")
def get_setting(
    request: Request,
    key: str,
    svc: KBService = Depends(get_kb_service),
):
    """Get a single setting (a secret value is masked)."""
    return SettingResponse(key=key, value=_masked_value(key, svc.db.get_setting(key)))


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
    svc: KBService = Depends(get_kb_service),
):
    """Set a single setting."""
    _require_admin_for(request, [key])
    _write(svc, key, req.value)
    return SettingResponse(key=key, value=_masked_value(key, svc.db.get_setting(key)))


@router.delete("/settings/{key}", dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def delete_setting(
    request: Request,
    key: str,
    svc: KBService = Depends(get_kb_service),
):
    """Delete a setting."""
    _require_admin_for(request, [key])
    deleted = svc.db.delete_setting(key)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Setting '{key}' not found"},
        )
    _maybe_invalidate_llm(key)
    return {"deleted": True, "key": key}
