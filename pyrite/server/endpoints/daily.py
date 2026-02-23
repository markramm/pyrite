"""Daily notes endpoint -- get or auto-create daily note for a given date."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...services.kb_service import KBService
from ..api import get_kb_service, limiter
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


@router.get("/daily/{date_str}", response_model=EntryResponse)
@limiter.limit("60/minute")
def get_or_create_daily_note(
    request: Request,
    date_str: str,
    kb: str = Query(..., description="KB name"),
    svc: KBService = Depends(get_kb_service),
):
    """Get or auto-create a daily note for the given date.

    If a daily note already exists (entry id = ``daily-YYYY-MM-DD``), it is
    returned.  Otherwise a new note is created from the ``daily`` template
    (if present in the KB's ``_templates/`` directory) or from a sensible
    default, then saved and indexed before being returned.
    """
    # Validate date
    try:
        parsed_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DATE",
                "message": f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.",
            },
        )

    if not svc.get_kb(kb):
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb}' not found"},
        )

    entry_id = _daily_entry_id(date_str)

    # Check if entry already exists in the index
    existing = svc.get_entry(entry_id, kb)
    if existing:
        existing.setdefault("sources", [])
        existing.setdefault("tags", [])
        existing.setdefault("outlinks", [])
        existing.setdefault("backlinks", [])
        return EntryResponse(**existing)

    # Try to load from disk (may not be indexed yet)
    loaded = svc.load_entry_from_disk(entry_id, kb)
    if loaded:
        svc.index_entry_from_disk(loaded, kb)
        result = svc.get_entry(entry_id, kb)
        if result:
            result.setdefault("sources", [])
            result.setdefault("tags", [])
            result.setdefault("outlinks", [])
            result.setdefault("backlinks", [])
            return EntryResponse(**result)

    # Auto-create from template or default
    title = f"Daily Note - {parsed_date.strftime('%Y-%m-%d')}"
    body = _default_daily_body(date_str)

    # Try to use a daily template if one exists
    try:
        from ...services.template_service import TemplateService

        tpl_svc = TemplateService(svc.config)
        rendered = tpl_svc.render_template(
            kb, "daily", variables={"title": title, "date": date_str}
        )
        body = rendered.get("body", body)
        fm_tags = rendered.get("frontmatter", {}).get("tags", [])
    except (FileNotFoundError, KeyError):
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
        # Fallback: construct response directly
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

    # Fallback: construct response directly
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
