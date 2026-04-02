"""Entry CRUD endpoints including wikilink resolution."""

import io
import logging

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
from ...config import PyriteConfig
from ..api import (
    get_config,
    get_kb_service,
    get_worktree_resolver,
    limiter,
    negotiate_response,
    requires_kb_tier,
)
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

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Entries"])


@router.get("/entries", response_model=EntryListResponse)
@limiter.limit("100/minute")
def list_entries(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB name"),
    entry_type: str | None = Query(None, description="Filter by entry type"),
    tag: str | None = Query(None, description="Filter by tag"),
    status: str | None = Query(None, description="Filter by status"),
    min_importance: int | None = Query(None, ge=1, le=10, description="Minimum importance (1-10)"),
    sort_by: str = Query("updated_at", description="Sort column"),
    sort_order: str = Query("desc", description="Sort direction: asc or desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: KBService = Depends(get_kb_service),
    resolver=Depends(get_worktree_resolver),
):
    """List entries with pagination."""
    # Use overlay so user sees their own edits in lists
    auth_user = getattr(request.state, "auth_user", None)
    if auth_user and kb:
        try:
            svc = resolver.get_read_service(kb, auth_user)
        except ValueError:
            pass  # KB not in a git repo — fall back to main

    results = svc.list_entries(
        kb_name=kb,
        entry_type=entry_type,
        tag=tag,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
        status=status,
        min_importance=min_importance,
    )
    total = svc.count_entries(
        kb_name=kb, entry_type=entry_type, tag=tag,
        status=status, min_importance=min_importance,
    )

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


@router.get("/entries/type-schemas")
@limiter.limit("100/minute")
def list_type_schemas(
    request: Request,
    kb: str | None = Query(None, description="KB name to get type schemas for"),
    config: "PyriteConfig" = Depends(get_config),
):
    """Return available entry types with field schemas for a KB.

    Merges type information from three sources:
    1. KB-level kb.yaml type definitions (highest priority)
    2. Plugin-registered entry types and presets
    3. Core built-in types (fallback)
    """
    from ...schema.core_types import CORE_TYPES, CORE_TYPE_METADATA

    result: dict[str, dict] = {}

    # Layer 1: Core types as baseline
    for type_name, type_info in CORE_TYPES.items():
        if type_name == "collection":
            continue  # internal type, skip
        fields = {}
        meta = CORE_TYPE_METADATA.get(type_name, {})
        field_descs = meta.get("field_descriptions", {})
        for fname, ftype in type_info.get("fields", {}).items():
            if fname in ("tags", "links"):
                continue
            fields[fname] = {
                "type": _python_type_to_field_type(ftype),
                "description": field_descs.get(fname, ""),
            }
        result[type_name] = {
            "description": type_info.get("description", ""),
            "fields": fields,
            "subdirectory": type_info.get("subdirectory", ""),
        }

    # Layer 2: Plugin entry types and presets
    try:
        from ...plugins import get_registry

        registry = get_registry()

        # Plugin presets — rich type definitions
        for _preset_name, preset_data in registry.get_all_kb_presets().items():
            for type_name, type_info in preset_data.get("types", {}).items():
                if type_name not in result:
                    result[type_name] = {"description": "", "fields": {}, "subdirectory": ""}
                result[type_name]["description"] = type_info.get("description", result[type_name]["description"])
                result[type_name]["subdirectory"] = type_info.get("subdirectory", result[type_name]["subdirectory"])
                # Add optional fields as field definitions
                for fname in type_info.get("optional", []):
                    if fname not in result[type_name]["fields"] and fname not in ("importance", "tags", "links"):
                        result[type_name]["fields"][fname] = {
                            "type": _guess_field_type(fname),
                            "description": "",
                        }

        # Plugin type metadata (field_descriptions, ai_instructions)
        for type_name, meta in registry.get_all_type_metadata().items():
            if type_name in result:
                for fname, desc in meta.get("field_descriptions", {}).items():
                    if fname in result[type_name]["fields"]:
                        result[type_name]["fields"][fname]["description"] = desc
    except Exception:
        logger.debug("Failed to load plugin type metadata", exc_info=True)

    # Layer 3: KB-level schema overrides (highest priority)
    if kb:
        kb_config = config.get_kb(kb)
        if kb_config:
            schema = kb_config.kb_schema
            for type_name, ts in schema.types.items():
                if type_name not in result:
                    result[type_name] = {"description": "", "fields": {}, "subdirectory": ""}
                if ts.description:
                    result[type_name]["description"] = ts.description
                if ts.subdirectory:
                    result[type_name]["subdirectory"] = ts.subdirectory
                if ts.file_pattern:
                    result[type_name]["file_pattern"] = ts.file_pattern
                # Rich field schemas from kb.yaml
                for fname, fs in ts.fields.items():
                    result[type_name]["fields"][fname] = fs.to_dict()
                    if fs.description:
                        result[type_name]["fields"][fname]["description"] = fs.description
                # Optional fields listed in kb.yaml
                for fname in ts.optional:
                    if fname not in result[type_name]["fields"] and fname not in ("importance", "tags", "links"):
                        result[type_name]["fields"][fname] = {
                            "type": _guess_field_type(fname),
                            "description": ts.field_descriptions.get(fname, ""),
                        }

    return {"types": result}


def _python_type_to_field_type(type_str: str) -> str:
    """Map Python type annotations to field schema types."""
    if "list" in type_str:
        return "list"
    if type_str in ("int", "float"):
        return "number"
    if type_str == "bool":
        return "checkbox"
    return "text"


def _guess_field_type(field_name: str) -> str:
    """Guess field type from the field name convention."""
    if field_name in ("date", "opened_date", "closed_date", "acquisition_date", "obtained_date", "founded"):
        return "date"
    if field_name in ("amount", "value", "importance"):
        return "number"
    if field_name in ("actors", "parties", "affiliations", "source_refs", "participants"):
        return "list"
    if field_name in ("url",):
        return "text"
    return "text"


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
    entries = []
    for r in rows:
        aliases_raw = r.get("aliases")
        if isinstance(aliases_raw, str):
            import json

            try:
                aliases = json.loads(aliases_raw) or []
            except (json.JSONDecodeError, TypeError):
                aliases = []
        elif isinstance(aliases_raw, list):
            aliases = aliases_raw
        else:
            aliases = []
        entries.append(
            EntryTitle(
                id=r["id"],
                title=r["title"],
                kb_name=r["kb_name"],
                entry_type=r["entry_type"],
                aliases=aliases,
            )
        )
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


@router.post("/entries/batch")
@limiter.limit("60/minute")
def batch_read_entries(
    request: Request,
    body: dict,
    svc: KBService = Depends(get_kb_service),
):
    """Batch-read multiple entries in one call."""
    entries_spec = body.get("entries", [])
    fields_param = body.get("fields")

    if not entries_spec:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_FAILED", "message": "entries array is required"},
        )
    if len(entries_spec) > 50:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_FAILED", "message": "Maximum 50 entries per call"},
        )

    ids = [(e["entry_id"], e["kb_name"]) for e in entries_spec]
    results = svc.get_entries(ids)

    if fields_param:
        results = [{k: r[k] for k in fields_param if k in r} for r in results]

    found_ids = {(r.get("id"), r.get("kb_name")) for r in results}
    not_found = [{"entry_id": eid, "kb_name": kb} for eid, kb in ids if (eid, kb) not in found_ids]

    resp_data = {"entries": results, "found": len(results), "not_found": not_found}
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return resp_data


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
    """Resolve a wikilink target to an entry. Tries exact ID match first, then title match.
    Supports fragment syntax: target#heading or target^block-id."""
    # Parse fragment from target
    heading = None
    block_id = None
    entry_target = target

    if "#" in target:
        entry_target, heading = target.split("#", 1)
    elif "^" in target:
        entry_target, block_id = target.split("^", 1)

    result = svc.resolve_entry(entry_target, kb_name=kb)

    if result:
        block_content = None
        # If fragment specified, try to find matching block
        if heading or block_id:
            from ...storage.models import Block

            blocks_query = svc.db.session.query(Block).filter_by(
                entry_id=result["id"], kb_name=result["kb_name"]
            )
            if heading:
                blocks_query = blocks_query.filter(Block.heading == heading)
            if block_id:
                blocks_query = blocks_query.filter(Block.block_id == block_id)
            block = blocks_query.first()
            if block:
                block_content = block.content

        return ResolveResponse(
            resolved=True,
            entry=EntryTitle(
                id=result["id"],
                title=result["title"],
                kb_name=result["kb_name"],
                entry_type=result["entry_type"],
            ),
            heading=heading,
            block_id=block_id,
            block_content=block_content,
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


@router.post("/entries/import", dependencies=[Depends(requires_kb_tier("write"))])
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
    fields: str | None = Query(None, description="Comma-separated fields to return"),
    svc: KBService = Depends(get_kb_service),
    resolver=Depends(get_worktree_resolver),
):
    """Get entry by ID."""
    # Use overlay so user sees their own edits
    auth_user = getattr(request.state, "auth_user", None)
    if auth_user and kb:
        try:
            svc = resolver.get_read_service(kb, auth_user)
        except ValueError:
            pass  # KB not in a git repo — fall back to main

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

    # Apply field projection
    if fields:
        fields_list = [f.strip() for f in fields.split(",")]
        result = {k: result[k] for k in fields_list if k in result}
        neg = negotiate_response(request, result)
        if neg is not None:
            return neg
        return result

    neg = negotiate_response(request, result)
    if neg is not None:
        return neg
    return EntryResponse(**result)


@router.post(
    "/entries", response_model=CreateResponse, dependencies=[Depends(requires_kb_tier("write"))]
)
@limiter.limit("30/minute")
def create_entry(
    request: Request,
    req: CreateEntryRequest,
    svc: KBService = Depends(get_kb_service),
    resolver=Depends(get_worktree_resolver),
):
    """Create a new entry."""
    # Route writes through worktree for authenticated users
    auth_user = getattr(request.state, "auth_user", None)
    if auth_user and auth_user.get("role") != "admin":
        try:
            svc = resolver.get_write_service(req.kb, auth_user)
        except ValueError:
            pass  # KB not in a git repo — fall back to main

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
            manager.broadcast({"type": "entry_created", "entry_id": entry.id, "kb_name": req.kb})
        )
    except RuntimeError:
        logger.debug("WebSocket broadcast failed (client may have disconnected)")

    return CreateResponse(created=True, id=entry.id, kb_name=req.kb, file_path="")


@router.put(
    "/entries/{entry_id}",
    response_model=UpdateResponse,
    dependencies=[Depends(requires_kb_tier("write"))],
)
@limiter.limit("30/minute")
def update_entry(
    request: Request,
    entry_id: str,
    req: UpdateEntryRequest,
    svc: KBService = Depends(get_kb_service),
    resolver=Depends(get_worktree_resolver),
):
    """Update an existing entry."""
    # Route writes through worktree for authenticated users
    auth_user = getattr(request.state, "auth_user", None)
    if auth_user and auth_user.get("role") != "admin":
        try:
            svc = resolver.get_write_service(req.kb, auth_user)
        except ValueError:
            pass  # KB not in a git repo — fall back to main

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
            manager.broadcast({"type": "entry_updated", "entry_id": entry_id, "kb_name": req.kb})
        )
    except RuntimeError:
        logger.debug("WebSocket broadcast failed (client may have disconnected)")

    return UpdateResponse(updated=True, id=entry_id)


@router.patch(
    "/entries/{entry_id}",
    response_model=UpdateResponse,
    dependencies=[Depends(requires_kb_tier("write"))],
)
@limiter.limit("30/minute")
def patch_entry_field(
    request: Request,
    entry_id: str,
    body: PatchEntryRequest,
    svc: KBService = Depends(get_kb_service),
    resolver=Depends(get_worktree_resolver),
):
    """Update a single field on an entry (used by kanban drag-drop)."""
    auth_user = getattr(request.state, "auth_user", None)
    if auth_user and auth_user.get("role") != "admin":
        try:
            svc = resolver.get_write_service(body.kb, auth_user)
        except (ValueError, Exception):
            logger.warning("Worktree routing failed for PATCH, falling back to main")

    try:
        svc.update_entry(entry_id, body.kb, **{body.field: body.value})
    except (KBNotFoundError, EntryNotFoundError) as e:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(e)})
    except KBReadOnlyError as e:
        raise HTTPException(status_code=403, detail={"code": "READ_ONLY", "message": str(e)})
    except (ValidationError, PyriteError, ValueError) as e:
        raise HTTPException(status_code=400, detail={"code": "UPDATE_FAILED", "message": str(e)})

    return UpdateResponse(updated=True, id=entry_id)


@router.delete(
    "/entries/{entry_id}",
    response_model=DeleteResponse,
    dependencies=[Depends(requires_kb_tier("write"))],
)
@limiter.limit("30/minute")
def delete_entry(
    request: Request,
    entry_id: str,
    kb: str = Query(..., description="KB name"),
    svc: KBService = Depends(get_kb_service),
    resolver=Depends(get_worktree_resolver),
):
    """Delete an entry."""
    # Route deletes through worktree for authenticated users
    auth_user = getattr(request.state, "auth_user", None)
    if auth_user and auth_user.get("role") != "admin":
        try:
            svc = resolver.get_write_service(kb, auth_user)
        except ValueError:
            pass  # KB not in a git repo — fall back to main

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
            manager.broadcast({"type": "entry_deleted", "entry_id": entry_id, "kb_name": kb})
        )
    except RuntimeError:
        logger.debug("WebSocket broadcast failed (client may have disconnected)")

    return DeleteResponse(deleted=True, id=entry_id)
