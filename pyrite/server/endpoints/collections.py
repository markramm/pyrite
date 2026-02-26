"""Collection endpoints — list and browse folder-backed and query-based collections."""

import json

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from ...exceptions import EntryNotFoundError
from ...plugins.registry import get_registry
from ...services.kb_service import KBService
from ..api import get_kb_service, limiter, negotiate_response
from ..schemas import (
    CollectionEntriesResponse,
    CollectionListResponse,
    CollectionResponse,
    EntryResponse,
    QueryPreviewRequest,
    QueryPreviewResponse,
)

router = APIRouter(tags=["Collections"])


def _parse_metadata(raw) -> dict:
    """Parse metadata which may be a JSON string or dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


@router.get("/collections/types")
@limiter.limit("100/minute")
def get_collection_types(request: Request):
    """Get available collection types (built-in + plugin-provided)."""
    built_in = {
        "generic": {
            "description": "General-purpose collection",
            "default_view": "list",
            "fields": {},
            "ai_instructions": "",
            "icon": "folder",
        },
    }
    plugin_types = get_registry().get_all_collection_types()
    # Plugin types override built-in on collision
    merged = {**built_in, **plugin_types}
    return {"types": merged}


@router.get("/collections", response_model=CollectionListResponse)
@limiter.limit("100/minute")
def list_collections(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB name"),
    svc: KBService = Depends(get_kb_service),
):
    """List all collections."""
    results = svc.list_collections(kb_name=kb)

    collections = []
    for r in results:
        meta = _parse_metadata(r.get("metadata"))
        collections.append(
            CollectionResponse(
                id=r["id"],
                title=r.get("title", ""),
                description=meta.get("description", ""),
                source_type=meta.get("source_type", "folder"),
                icon=meta.get("icon", ""),
                view_config=meta.get("view_config", {}),
                entry_count=0,
                kb_name=r.get("kb_name", ""),
                folder_path=meta.get("folder_path", ""),
                query=meta.get("query", ""),
                tags=r.get("tags", []),
            )
        )

    resp_data = {
        "collections": [c.model_dump() for c in collections],
        "total": len(collections),
    }
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return CollectionListResponse(collections=collections, total=len(collections))


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
@limiter.limit("100/minute")
def get_collection(
    request: Request,
    collection_id: str,
    kb: str = Query(..., description="KB name"),
    svc: KBService = Depends(get_kb_service),
):
    """Get collection metadata."""
    result = svc.get_entry(collection_id, kb_name=kb)
    if not result or result.get("entry_type") != "collection":
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Collection '{collection_id}' not found"},
        )

    meta = _parse_metadata(result.get("metadata"))
    resp = CollectionResponse(
        id=result["id"],
        title=result.get("title", ""),
        description=meta.get("description", ""),
        source_type=meta.get("source_type", "folder"),
        icon=meta.get("icon", ""),
        view_config=meta.get("view_config", {}),
        entry_count=0,
        kb_name=result.get("kb_name", ""),
        folder_path=meta.get("folder_path", ""),
        query=meta.get("query", ""),
        tags=result.get("tags", []),
    )

    neg = negotiate_response(request, resp.model_dump())
    if neg is not None:
        return neg
    return resp


@router.get("/collections/{collection_id}/entries", response_model=CollectionEntriesResponse)
@limiter.limit("100/minute")
def get_collection_entries(
    request: Request,
    collection_id: str,
    kb: str = Query(..., description="KB name"),
    sort_by: str = Query("title", description="Sort column"),
    sort_order: str = Query("asc", description="Sort direction: asc or desc"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: KBService = Depends(get_kb_service),
):
    """List entries within a collection."""
    try:
        results, total = svc.get_collection_entries(
            collection_id, kb,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
    except EntryNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": str(e)},
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
        "collection_id": collection_id,
    }
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return CollectionEntriesResponse(entries=entries, total=total, collection_id=collection_id)


@router.post("/collections/query-preview", response_model=QueryPreviewResponse)
@limiter.limit("60/minute")
def preview_collection_query(
    request: Request,
    body: QueryPreviewRequest = Body(...),
    svc: KBService = Depends(get_kb_service),
):
    """Preview results for a collection query without saving."""
    from ...services.collection_query import (
        evaluate_query,
        parse_query,
        validate_query,
    )

    query = parse_query(body.query)
    if body.kb:
        query.kb_name = body.kb
    query.limit = body.limit

    errors = validate_query(query)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_QUERY", "message": "; ".join(errors)},
        )

    results, total = evaluate_query(query, svc.db)

    entries = []
    for r in results:
        r.setdefault("sources", [])
        r.setdefault("tags", [])
        r.setdefault("outlinks", [])
        r.setdefault("backlinks", [])
        entries.append(EntryResponse(**r))

    query_parsed = {
        "entry_type": query.entry_type,
        "tags_any": query.tags_any,
        "tags_all": query.tags_all,
        "status": query.status,
        "kb_name": query.kb_name,
        "date_from": query.date_from,
        "date_to": query.date_to,
        "sort_by": query.sort_by,
        "sort_order": query.sort_order,
        "limit": query.limit,
    }

    resp_data = {
        "entries": [e.model_dump() for e in entries],
        "total": total,
        "query_parsed": query_parsed,
    }
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return QueryPreviewResponse(entries=entries, total=total, query_parsed=query_parsed)
