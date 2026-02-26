"""Entry CRUD endpoints including wikilink resolution."""

import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from ...exceptions import (
    EntryNotFoundError,
    KBNotFoundError,
    KBReadOnlyError,
    PyriteError,
    ValidationError,
)
from ...services.kb_service import KBService
from ..api import get_kb_service, limiter, negotiate_response, requires_tier
from ..schemas import (
    CreateEntryRequest,
    CreateResponse,
    DeleteResponse,
    EntryListResponse,
    EntryResponse,
    EntryTitle,
    EntryTitlesResponse,
    EntryTypesResponse,
    PatchEntryRequest,
    ResolveBatchRequest,
    ResolveBatchResponse,
    ResolveResponse,
    UpdateEntryRequest,
    UpdateResponse,
    WantedPage,
    WantedPagesResponse,
)

router = APIRouter(tags=["Entries"])


@router.get("/entries", response_model=EntryListResponse)
@limiter.limit("100/minute")
def list_entries(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB name"),
    entry_type: str | None = Query(None, description="Filter by entry type"),
    tag: str | None = Query(None, description="Filter by tag"),
    sort_by: str = Query("updated_at", description="Sort column"),
    sort_order: str = Query("desc", description="Sort direction: asc or desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: KBService = Depends(get_kb_service),
):
    """List entries with pagination."""
    results = svc.list_entries(
        kb_name=kb,
        entry_type=entry_type,
        tag=tag,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    total = svc.count_entries(kb_name=kb, entry_type=entry_type, tag=tag)

    entries = []
    for r in results:
        r.setdefault("sources", [])
        r.setdefault("tags", [])
        r.setdefault("outlinks", [])
        r.setdefault("backlinks", [])
        entries.append(EntryResponse(**r))

    resp_data = {
        "entries": [e.model_dump() for e in entries],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return EntryListResponse(entries=entries, total=total, limit=limit, offset=offset)


@router.get("/entries/types", response_model=EntryTypesResponse)
@limiter.limit("100/minute")
def list_entry_types(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB name"),
    svc: KBService = Depends(get_kb_service),
):
    """Get distinct entry types."""
    types = svc.get_distinct_types(kb_name=kb)
    return EntryTypesResponse(types=types)


@router.get("/entries/titles", response_model=EntryTitlesResponse)
@limiter.limit("100/minute")
def list_entry_titles(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB name"),
    q: str | None = Query(None, description="Filter titles by search string"),
    limit: int = Query(500, ge=1, le=5000),
    svc: KBService = Depends(get_kb_service),
):
    """Lightweight listing of entry IDs and titles for wikilink autocomplete."""
    rows = svc.list_entry_titles(kb_name=kb, query=q, limit=limit)
    entries = [
        EntryTitle(id=r["id"], title=r["title"], kb_name=r["kb_name"], entry_type=r["entry_type"])
        for r in rows
    ]
    return EntryTitlesResponse(entries=entries)


@router.post("/entries/resolve-batch", response_model=ResolveBatchResponse)
@limiter.limit("100/minute")
def resolve_batch(
    request: Request,
    req: ResolveBatchRequest,
    svc: KBService = Depends(get_kb_service),
):
    """Batch-resolve wikilink targets. Returns which targets exist."""
    resolved = svc.resolve_batch(req.targets, kb_name=req.kb)
    return ResolveBatchResponse(resolved=resolved)


@router.get("/entries/wanted", response_model=WantedPagesResponse)
@limiter.limit("100/minute")
def list_wanted_pages(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB name"),
    limit: int = Query(100, ge=1, le=500),
    svc: KBService = Depends(get_kb_service),
):
    """List link targets that don't exist as entries (wanted pages)."""
    pages = svc.get_wanted_pages(kb_name=kb, limit=limit)
    result = []
    for p in pages:
        refs = p.get("referenced_by", "") or ""
        ref_list = [r for r in refs.split(",") if r] if isinstance(refs, str) else []
        result.append(
            WantedPage(
                target_id=p["target_id"],
                target_kb=p["target_kb"],
                ref_count=p["ref_count"],
                referenced_by=ref_list,
            )
        )
    return WantedPagesResponse(count=len(result), pages=result)


@router.get("/entries/resolve", response_model=ResolveResponse)
@limiter.limit("100/minute")
def resolve_entry(
    request: Request,
    target: str = Query(..., description="Entry ID or title to resolve"),
    kb: str | None = Query(None, description="Filter by KB name"),
    svc: KBService = Depends(get_kb_service),
):
    """Resolve a wikilink target to an entry. Tries exact ID match first, then title match."""
    result = svc.resolve_entry(target, kb_name=kb)

    if result:
        return ResolveResponse(
            resolved=True,
            entry=EntryTitle(
                id=result["id"],
                title=result["title"],
                kb_name=result["kb_name"],
                entry_type=result["entry_type"],
            ),
        )
    return ResolveResponse(resolved=False, entry=None)


# =============================================================================
# Import / Export (must be before /entries/{entry_id} to avoid route conflicts)
# =============================================================================


@router.get("/entries/export")
@limiter.limit("30/minute")
def export_entries(
    request: Request,
    kb: str = Query(..., description="KB to export"),
    format: str = Query("json", description="Export format: json, markdown, csv"),
    entry_type: str | None = Query(None, description="Filter by entry type"),
    tag: str | None = Query(None, description="Filter by tag"),
    limit: int = Query(10000, ge=1, le=50000),
    svc: KBService = Depends(get_kb_service),
):
    """Export entries as JSON, Markdown, or CSV."""
    from ...formats import get_format_registry

    if not svc.get_kb(kb):
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb}' not found"},
        )

    entries = svc.list_entries(kb_name=kb, entry_type=entry_type, limit=limit, offset=0)

    # For full export, load bodies from disk
    full_entries = []
    for e in entries:
        full = svc.get_entry(e["id"], kb_name=kb)
        if full:
            # Apply tag filter if specified
            if tag and tag not in full.get("tags", []):
                continue
            full_entries.append(full)

    registry = get_format_registry()
    fmt_spec = registry.get(format)
    if not fmt_spec:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSUPPORTED_FORMAT",
                "message": f"Unsupported format: {format}",
            },
        )

    data = {"entries": full_entries, "total": len(full_entries)}
    content = fmt_spec.serializer(data)

    ext = fmt_spec.file_extension
    filename = f"{kb}-export.{ext}"

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type=fmt_spec.media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/entries/import", dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
async def import_entries(
    request: Request,
    file: UploadFile = File(...),
    kb: str = Query(..., description="Target KB name"),
    format: str = Query(
        None, description="Format: json, markdown, csv (auto-detected from extension if omitted)"
    ),
    svc: KBService = Depends(get_kb_service),
):
    """Import entries from an uploaded file."""
    from ...formats.importers import get_importer_registry
    from ...schema import generate_entry_id

    if not svc.get_kb(kb):
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{kb}' not found"},
        )

    # Auto-detect format from filename
    fmt = format
    if not fmt and file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        fmt = {"json": "json", "md": "markdown", "csv": "csv"}.get(ext)
    if not fmt:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "FORMAT_REQUIRED",
                "message": "Could not detect format. Specify format=json|markdown|csv",
            },
        )

    registry = get_importer_registry()
    importer = registry.get(fmt)
    if not importer:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSUPPORTED_FORMAT",
                "message": f"Unsupported format: {fmt}. Available: {registry.available_formats()}",
            },
        )

    content = await file.read()
    try:
        parsed = importer(content)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "PARSE_ERROR", "message": f"Failed to parse file: {e}"},
        )

    created = []
    errors = []
    for entry_data in parsed:
        try:
            entry_id = entry_data.get("id") or generate_entry_id(entry_data["title"])
            entry_type = entry_data.get("entry_type", "note")
            extra = {
                k: v
                for k, v in entry_data.items()
                if k not in ("id", "title", "entry_type", "body") and v is not None
            }
            entry = svc.create_entry(
                kb, entry_id, entry_data["title"], entry_type, entry_data.get("body", ""), **extra
            )
            created.append({"id": entry.id, "title": entry.title})
        except Exception as e:
            errors.append({"title": entry_data.get("title", "?"), "error": str(e)})

    return {
        "imported": len(created),
        "errors": len(errors),
        "entries": created,
        "error_details": errors,
    }


# =============================================================================
# Entry CRUD (parametric routes must come after static routes)
# =============================================================================


@router.get("/entries/{entry_id}", response_model=EntryResponse)
@limiter.limit("100/minute")
def get_entry(
    request: Request,
    entry_id: str,
    kb: str | None = Query(None, description="KB name (optional)"),
    with_links: bool = Query(False, description="Include links"),
    svc: KBService = Depends(get_kb_service),
):
    """Get entry by ID."""
    if with_links:
        # get_entry already includes outlinks/backlinks
        result = svc.get_entry(entry_id, kb_name=kb)
    else:
        # For non-link requests, get entry without links
        result = svc.get_entry(entry_id, kb_name=kb)
        if result:
            result.setdefault("outlinks", [])
            result.setdefault("backlinks", [])

    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": f"Entry '{entry_id}' not found",
                "hint": f"Search: /api/search?q={entry_id}",
            },
        )

    result.setdefault("sources", [])
    result.setdefault("tags", [])

    neg = negotiate_response(request, result)
    if neg is not None:
        return neg
    return EntryResponse(**result)


@router.post("/entries", response_model=CreateResponse, dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def create_entry(
    request: Request,
    req: CreateEntryRequest,
    svc: KBService = Depends(get_kb_service),
):
    """Create a new entry."""
    if not svc.get_kb(req.kb):
        raise HTTPException(
            status_code=404,
            detail={"code": "KB_NOT_FOUND", "message": f"KB '{req.kb}' not found"},
        )

    if req.entry_type == "event" and not req.date:
        raise HTTPException(
            status_code=400,
            detail={"code": "MISSING_DATE", "message": "Events require a date"},
        )

    # Filter out None values so factory defaults apply
    extra = {
        k: v
        for k, v in {
            "date": req.date,
            "importance": req.importance,
            "participants": req.participants,
            "role": req.role,
            "tags": req.tags,
            "metadata": req.metadata,
        }.items()
        if v is not None
    }

    from ...schema import generate_entry_id

    entry_id = generate_entry_id(req.title)

    try:
        entry = svc.create_entry(
            req.kb, entry_id, req.title, req.entry_type or "note", req.body, **extra
        )
    except (KBNotFoundError, EntryNotFoundError) as e:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(e)})
    except KBReadOnlyError as e:
        raise HTTPException(status_code=403, detail={"code": "READ_ONLY", "message": str(e)})
    except (ValidationError, PyriteError, ValueError) as e:
        raise HTTPException(status_code=400, detail={"code": "CREATE_FAILED", "message": str(e)})

    # Broadcast WebSocket event
    import asyncio

    from ..websocket import manager

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(
            manager.broadcast(
                {"type": "entry_created", "entry_id": entry.id, "kb_name": req.kb}
            )
        )
    except RuntimeError:
        pass

    return CreateResponse(created=True, id=entry.id, kb_name=req.kb, file_path="")


@router.put("/entries/{entry_id}", response_model=UpdateResponse, dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def update_entry(
    request: Request,
    entry_id: str,
    req: UpdateEntryRequest,
    svc: KBService = Depends(get_kb_service),
):
    """Update an existing entry."""
    updates = {}
    if req.title is not None:
        updates["title"] = req.title
    if req.body is not None:
        updates["body"] = req.body
    if req.importance is not None:
        updates["importance"] = req.importance
    if req.tags is not None:
        updates["tags"] = req.tags

    try:
        svc.update_entry(entry_id, req.kb, **updates)
    except (KBNotFoundError, EntryNotFoundError) as e:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(e)})
    except KBReadOnlyError as e:
        raise HTTPException(status_code=403, detail={"code": "READ_ONLY", "message": str(e)})
    except (ValidationError, PyriteError, ValueError) as e:
        raise HTTPException(status_code=400, detail={"code": "UPDATE_FAILED", "message": str(e)})

    # Broadcast WebSocket event
    import asyncio

    from ..websocket import manager

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(
            manager.broadcast(
                {"type": "entry_updated", "entry_id": entry_id, "kb_name": req.kb}
            )
        )
    except RuntimeError:
        pass

    return UpdateResponse(updated=True, id=entry_id)


@router.patch("/entries/{entry_id}", response_model=UpdateResponse, dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def patch_entry_field(
    request: Request,
    entry_id: str,
    body: PatchEntryRequest,
    svc: KBService = Depends(get_kb_service),
):
    """Update a single field on an entry (used by kanban drag-drop)."""
    try:
        svc.update_entry(entry_id, body.kb, **{body.field: body.value})
    except (KBNotFoundError, EntryNotFoundError) as e:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(e)})
    except KBReadOnlyError as e:
        raise HTTPException(status_code=403, detail={"code": "READ_ONLY", "message": str(e)})
    except (ValidationError, PyriteError, ValueError) as e:
        raise HTTPException(status_code=400, detail={"code": "UPDATE_FAILED", "message": str(e)})

    return UpdateResponse(updated=True, id=entry_id)


@router.delete("/entries/{entry_id}", response_model=DeleteResponse, dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def delete_entry(
    request: Request,
    entry_id: str,
    kb: str = Query(..., description="KB name"),
    svc: KBService = Depends(get_kb_service),
):
    """Delete an entry."""
    try:
        deleted = svc.delete_entry(entry_id, kb)
    except (KBNotFoundError, EntryNotFoundError) as e:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(e)})
    except KBReadOnlyError as e:
        raise HTTPException(status_code=403, detail={"code": "READ_ONLY", "message": str(e)})
    except (ValidationError, PyriteError, ValueError) as e:
        raise HTTPException(status_code=400, detail={"code": "DELETE_FAILED", "message": str(e)})

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Entry '{entry_id}' not found"},
        )

    # Broadcast WebSocket event
    import asyncio

    from ..websocket import manager

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(
            manager.broadcast(
                {"type": "entry_deleted", "entry_id": entry_id, "kb_name": kb}
            )
        )
    except RuntimeError:
        pass

    return DeleteResponse(deleted=True, id=entry_id)
