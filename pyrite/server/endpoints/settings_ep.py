"""Settings endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ...services.kb_service import KBService
from ..api import get_kb_service, invalidate_llm_service, limiter, requires_tier
from ..schemas import (
    BulkSettingsUpdateRequest,
    SettingResponse,
    SettingsResponse,
    SettingUpdateRequest,
)

router = APIRouter(tags=["Settings"])

# Settings keys that require LLM service invalidation on change
_AI_SETTINGS_PREFIXES = ("ai.",)


def _maybe_invalidate_llm(key: str) -> None:
    """Invalidate cached LLM service if an AI setting changed."""
    if any(key.startswith(p) for p in _AI_SETTINGS_PREFIXES):
        invalidate_llm_service()


@router.get("/settings", response_model=SettingsResponse)
@limiter.limit("100/minute")
def get_all_settings(
    request: Request,
    svc: KBService = Depends(get_kb_service),
):
    """Get all settings."""
    settings = svc.get_all_settings()
    return SettingsResponse(settings=settings)


@router.put("/settings", dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def bulk_update_settings(
    request: Request,
    req: BulkSettingsUpdateRequest,
    svc: KBService = Depends(get_kb_service),
):
    """Bulk update settings."""
    for key, value in req.settings.items():
        svc.set_setting(key, value)
        _maybe_invalidate_llm(key)
    return SettingsResponse(settings=svc.get_all_settings())


@router.get("/settings/{key}", response_model=SettingResponse)
@limiter.limit("100/minute")
def get_setting(
    request: Request,
    key: str,
    svc: KBService = Depends(get_kb_service),
):
    """Get a single setting."""
    value = svc.get_setting(key)
    return SettingResponse(key=key, value=value)


@router.put("/settings/{key}", response_model=SettingResponse, dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def set_setting(
    request: Request,
    key: str,
    req: SettingUpdateRequest,
    svc: KBService = Depends(get_kb_service),
):
    """Set a single setting."""
    svc.set_setting(key, req.value)
    _maybe_invalidate_llm(key)
    return SettingResponse(key=key, value=req.value)


@router.delete("/settings/{key}", dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def delete_setting(
    request: Request,
    key: str,
    svc: KBService = Depends(get_kb_service),
):
    """Delete a setting."""
    deleted = svc.delete_setting(key)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Setting '{key}' not found"},
        )
    _maybe_invalidate_llm(key)
    return {"deleted": True, "key": key}
