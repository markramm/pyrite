"""Search endpoint."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from ...services.kb_service import KBService
from ...services.search_service import SearchService
from ..api import (
    get_kb_service,
    get_readable_kbs,
    get_search_service,
    limiter,
    negotiate_response,
    requires_kb_read,
)
from ..schemas import SearchResponse, SearchResult

router = APIRouter(tags=["Search"])


# ``response_model_exclude_none``: the happy path must not serialise
# ``"warnings": null``. One convention across every surface — MCP omits the key,
# the CLI prints nothing, REST omits it — so a caller can test ``"warnings" in
# response`` and get the right answer. See ``SearchService.search``'s docstring
# for what a search response owes its caller (#56). The web client already
# declares the nullable result fields optional (web/src/lib/api/types.ts), so
# omitting them rather than nulling them matches the contract it was written to.
@router.get(
    "/search",
    response_model=SearchResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(requires_kb_read())],
)
@limiter.limit("100/minute")
def search(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    kb: str | None = Query(None, description="Limit to specific KB"),
    type: str | None = Query(None, description="Filter by entry type"),
    tags: str | None = Query(None, description="Comma-separated tags"),
    date_from: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    limit: int = Query(20, ge=1, le=100),
    mode: str = Query("keyword", description="Search mode: keyword, semantic, hybrid"),
    expand: bool = Query(False, description="Use AI query expansion for additional search terms"),
    include_body: bool = Query(
        False, description="Include full body text in results (default: snippet only)"
    ),
    fields: str | None = Query(
        None,
        description=(
            "Comma-separated fields to return per result. "
            "id and kb_name are always included; when fields is set the response is a "
            "projection of the stored entry, not EntryResponse."
        ),
    ),
    group_by_kb: bool = Query(
        False, description="Return top results per KB instead of global ranking"
    ),
    limit_per_kb: int = Query(
        3, ge=1, le=20, description="Max results per KB when group_by_kb=true"
    ),
    svc: KBService = Depends(get_kb_service),
    search_svc: SearchService = Depends(get_search_service),
    readable: set[str] | None = Depends(get_readable_kbs),
):
    """Full-text search across the knowledge bases the caller may read."""
    if svc.count_entries() == 0:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "INDEX_EMPTY",
                "message": "Search index is empty",
                "hint": "Run: pyrite-admin index build",
            },
        )

    tag_list = tags.split(",") if tags else None
    # Anything the search could not do as asked (today: a filter a backend's
    # vector leg cannot honour). Omitted from the response when empty -- see the
    # route decorator above and SearchService.search's docstring (#56).
    warnings: list[str] = []

    try:
        # When grouping by KB, fetch more results to ensure coverage across KBs
        fetch_limit = limit * 5 if group_by_kb else limit

        results = search_svc.search(
            kb_names=None if kb else readable,
            query=q,
            kb_name=kb,
            entry_type=type,
            tags=tag_list,
            date_from=date_from,
            date_to=date_to,
            limit=fetch_limit,
            mode=mode,
            expand=expand,
            warnings=warnings,
        )

        # Group by KB: take top N per KB, interleave by best score
        if group_by_kb:
            from collections import defaultdict

            by_kb: dict[str, list] = defaultdict(list)
            for r in results:
                kb_name_val = r.get("kb_name", "")
                if len(by_kb[kb_name_val]) < limit_per_kb:
                    by_kb[kb_name_val].append(r)
            # Interleave: round-robin by best score in each group
            grouped: list = []
            remaining = dict(by_kb)
            while remaining:
                exhausted = []
                for k in sorted(
                    remaining,
                    key=lambda k: remaining[k][0].get("score", 0) if remaining[k] else 0,
                    reverse=True,
                ):
                    if remaining[k]:
                        grouped.append(remaining[k].pop(0))
                    if not remaining[k]:
                        exhausted.append(k)
                for k in exhausted:
                    del remaining[k]
            results = grouped[:limit]

        # Apply field projection or strip body
        if fields:
            fields_list = [f.strip() for f in fields.split(",")]
            projected_fields = dict.fromkeys(("id", "kb_name", *fields_list))
            results = [{k: r[k] for k in projected_fields if k in r} for r in results]
        elif not include_body:
            for r in results:
                r.pop("body", None)

        resp_data = {"query": q, "count": len(results), "results": results}
        if warnings:
            resp_data["warnings"] = warnings
        neg = negotiate_response(request, resp_data)
        if neg is not None:
            return neg
        if fields:
            return JSONResponse(content=resp_data)
        return SearchResponse(
            query=q,
            count=len(results),
            results=[SearchResult(**r) for r in results],
            warnings=warnings or None,
        )
    except (sqlite3.OperationalError, ValueError) as e:
        raise HTTPException(status_code=400, detail={"code": "SEARCH_FAILED", "message": str(e)})
