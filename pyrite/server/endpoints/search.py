"""Search endpoint."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...services.kb_service import KBService
from ...services.search_service import SearchService
from ..api import get_kb_service, get_search_service, limiter, negotiate_response
from ..schemas import SearchResponse, SearchResult

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=SearchResponse)
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
    svc: KBService = Depends(get_kb_service),
    search_svc: SearchService = Depends(get_search_service),
):
    """Full-text search across knowledge bases."""
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

    try:
        results = search_svc.search(
            query=q,
            kb_name=kb,
            entry_type=type,
            tags=tag_list,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            mode=mode,
            expand=expand,
        )

        resp_data = {"query": q, "count": len(results), "results": results}
        neg = negotiate_response(request, resp_data)
        if neg is not None:
            return neg
        return SearchResponse(
            query=q, count=len(results), results=[SearchResult(**r) for r in results]
        )
    except (sqlite3.OperationalError, ValueError) as e:
        raise HTTPException(status_code=400, detail={"code": "SEARCH_FAILED", "message": str(e)})
