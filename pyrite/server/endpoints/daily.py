"""Daily notes endpoint -- get or auto-create daily note for a given date."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...config import PyriteConfig
from ...exceptions import KBNotFoundError
from ...services.kb_service import KBService
from ...storage.database import PyriteDB
from ..api import (
    TIER_LEVELS,
    get_config,
    get_db,
    get_kb_service,
    limiter,
    requires_kb_tier,
    resolve_effective_kb_role,
)
from ..schemas import DailyDatesResponse, EntryResponse

router = APIRouter(tags=["Daily Notes"])


def _daily_entry_id(date_str: str) -> str:
    """Generate a consistent entry ID for a daily note."""
    return f"daily-{date_str}"


def _default_daily_body(date_str: str) -> str:
    """Default daily note body when no template exists."""
    d = date.fromisoformat(date_str)
    return f"# {d.strftime('%A, %B %-d, %Y')}\n\n"


@router.get("/daily/dates", response_model=DailyDatesResponse)
@limiter.limit("60/minute")
def list_daily_dates(
    request: Request,
    kb: str = Query(..., description="KB name"),
    month: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Filter by month (YYYY-MM). Defaults to current month.",
    ),
    svc: KBService = Depends(get_kb_service),
):
    """List dates that have daily notes for calendar display."""
    if not svc.get_kb(kb):
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb}' not found"},
        )

    if month is None:
        month = datetime.now(UTC).strftime("%Y-%m")

    dates = svc.list_daily_dates(kb, month)
    return DailyDatesResponse(dates=dates)


def _load_existing_daily_note(svc: KBService, entry_id: str, kb: str) -> EntryResponse | None:
    """Return the daily note if it's already indexed or present on disk
    (indexing it first in the latter case). None if it doesn't exist yet."""
    existing = svc.get_entry(entry_id, kb)
    if not existing:
        loaded = svc.load_entry_from_disk(entry_id, kb)
        if loaded:
            svc.index_entry_from_disk(loaded, kb)
            existing = svc.get_entry(entry_id, kb)

    if not existing:
        return None
    existing.setdefault("sources", [])
    existing.setdefault("tags", [])
    existing.setdefault("outlinks", [])
    existing.setdefault("backlinks", [])
    return EntryResponse(**existing)


def _create_daily_note(svc: KBService, entry_id: str, kb: str, date_str: str) -> EntryResponse:
    """Create a new daily note from the ``daily`` template (if present) or
    a sensible default, save and index it, and return the result."""
    parsed_date = date.fromisoformat(date_str)
    title = f"Daily Note - {parsed_date.strftime('%Y-%m-%d')}"
    body = _default_daily_body(date_str)

    try:
        from ...services.template_service import TemplateService

        tpl_svc = TemplateService(svc.config)
        rendered = tpl_svc.render_template(
            kb, "daily", variables={"title": title, "date": date_str}
        )
        body = rendered.get("body", body)
        fm_tags = rendered.get("frontmatter", {}).get("tags", [])
    except (FileNotFoundError, KeyError, KBNotFoundError):
        fm_tags = ["daily"]

    try:
        svc.create_entry(
            kb,
            entry_id,
            title,
            "note",
            body,
            tags=fm_tags if fm_tags else ["daily"],
        )
    except ValueError:
        now = datetime.now(UTC)
        return EntryResponse(
            id=entry_id,
            kb_name=kb,
            entry_type="note",
            title=title,
            body=body,
            tags=fm_tags if fm_tags else ["daily"],
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        )

    result = svc.get_entry(entry_id, kb)
    if result:
        result.setdefault("sources", [])
        result.setdefault("tags", [])
        result.setdefault("outlinks", [])
        result.setdefault("backlinks", [])
        return EntryResponse(**result)

    now = datetime.now(UTC)
    return EntryResponse(
        id=entry_id,
        kb_name=kb,
        entry_type="note",
        title=title,
        body=body,
        tags=fm_tags if fm_tags else ["daily"],
        file_path="",
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
    )


def _validate_date(date_str: str) -> None:
    try:
        date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DATE",
                "message": f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.",
            },
        )


@router.get("/daily/{date_str}", response_model=EntryResponse)
@limiter.limit("60/minute")
async def get_or_create_daily_note(
    request: Request,
    date_str: str,
    kb: str = Query(..., description="KB name"),
    svc: KBService = Depends(get_kb_service),
    config: PyriteConfig = Depends(get_config),
    db: PyriteDB = Depends(get_db),
):
    """Get a daily note for the given date, auto-creating it only for a
    write-tier caller.

    If a daily note already exists (entry id = ``daily-YYYY-MM-DD``), it is
    returned regardless of tier. Otherwise, a write-tier caller gets a new
    note created from the ``daily`` template (if present in the KB's
    ``_templates/`` directory) or from a sensible default. A caller
    without write access on this KB never triggers creation -- merely
    viewing/navigating must not have write side effects
    (web-daily-notes-view-side-effect) -- and gets 404 instead; the
    frontend uses `POST /daily/{date_str}` to create explicitly.
    """
    _validate_date(date_str)

    if not svc.get_kb(kb):
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb}' not found"},
        )

    entry_id = _daily_entry_id(date_str)

    existing = _load_existing_daily_note(svc, entry_id, kb)
    if existing:
        return existing

    effective_role = await resolve_effective_kb_role(request, config, db, kb)
    if effective_role is None or TIER_LEVELS.get(effective_role, -1) < TIER_LEVELS.get("write", 99):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": f"No daily note for '{date_str}' in KB '{kb}'",
            },
        )

    return _create_daily_note(svc, entry_id, kb, date_str)


@router.post(
    "/daily/{date_str}",
    response_model=EntryResponse,
    dependencies=[Depends(requires_kb_tier("write"))],
)
@limiter.limit("60/minute")
def create_daily_note(
    request: Request,
    date_str: str,
    kb: str = Query(..., description="KB name"),
    svc: KBService = Depends(get_kb_service),
):
    """Explicitly create (or return, if already existing) a daily note.

    Write-tier only. This is the action a "Start today's note" button
    calls -- unlike the GET endpoint, this is never triggered by mere
    navigation/viewing.
    """
    _validate_date(date_str)

    if not svc.get_kb(kb):
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb}' not found"},
        )

    entry_id = _daily_entry_id(date_str)

    existing = _load_existing_daily_note(svc, entry_id, kb)
    if existing:
        return existing

    return _create_daily_note(svc, entry_id, kb, date_str)
