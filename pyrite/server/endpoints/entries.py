"""Entry CRUD endpoints including wikilink resolution."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...services.kb_service import KBService
from ..api import get_kb_service, limiter, negotiate_response
from ..schemas import (
    CreateEntryRequest,
    CreateResponse,
    DeleteResponse,
    EntryListResponse,
    EntryResponse,
    EntryTitle,
    EntryTitlesResponse,
    ResolveResponse,
    UpdateEntryRequest,
    UpdateResponse,
)

router = APIRouter(tags=["Entries"])


@router.get("/entries", response_model=EntryListResponse)
@limiter.limit("100/minute")
def list_entries(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB name"),
    entry_type: str | None = Query(None, description="Filter by entry type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: KBService = Depends(get_kb_service),
):
    """List entries with pagination."""
    results = svc.list_entries(kb_name=kb, entry_type=entry_type, limit=limit, offset=offset)
    total = svc.count_entries(kb_name=kb, entry_type=entry_type)

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


@router.post("/entries", response_model=CreateResponse)
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "CREATE_FAILED", "message": str(e)})

    return CreateResponse(created=True, id=entry.id, kb_name=req.kb, file_path="")


@router.put("/entries/{entry_id}", response_model=UpdateResponse)
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
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": msg},
            )
        raise HTTPException(status_code=400, detail={"code": "UPDATE_FAILED", "message": msg})

    return UpdateResponse(updated=True, id=entry_id)


@router.delete("/entries/{entry_id}", response_model=DeleteResponse)
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
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": msg},
            )
        raise HTTPException(status_code=400, detail={"code": "DELETE_FAILED", "message": msg})

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Entry '{entry_id}' not found"},
        )

    return DeleteResponse(deleted=True, id=entry_id)
