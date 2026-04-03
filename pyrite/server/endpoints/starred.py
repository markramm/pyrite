"""Starred/bookmarked entries endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...services.starred_service import StarredService
from ..api import get_starred_service, limiter, requires_tier
from ..schemas import (
    ReorderStarredRequest,
    ReorderStarredResponse,
    StarEntryRequest,
    StarEntryResponse,
    StarredEntryItem,
    StarredEntryListResponse,
    UnstarEntryResponse,
)

router = APIRouter(tags=["Starred"])


@router.get("/starred", response_model=StarredEntryListResponse)
@limiter.limit("100/minute")
def list_starred(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB name"),
    svc: StarredService = Depends(get_starred_service),
):
    """List all starred entries, optionally filtered by KB."""
    items = svc.list_starred(kb=kb)
    return StarredEntryListResponse(
        count=len(items),
        starred=[StarredEntryItem(**item) for item in items],
    )


@router.post(
    "/starred", response_model=StarEntryResponse, dependencies=[Depends(requires_tier("write"))]
)
@limiter.limit("30/minute")
def star_entry(
    request: Request,
    body: StarEntryRequest,
    svc: StarredService = Depends(get_starred_service),
):
    """Star/bookmark an entry. Idempotent — starring an already-starred entry succeeds."""
    result = svc.star_entry(entry_id=body.entry_id, kb_name=body.kb_name)
    return StarEntryResponse(**result)


@router.delete(
    "/starred/{entry_id}",
    response_model=UnstarEntryResponse,
    dependencies=[Depends(requires_tier("write"))],
)
@limiter.limit("30/minute")
def unstar_entry(
    request: Request,
    entry_id: str,
    kb: str | None = Query(None, description="KB name"),
    svc: StarredService = Depends(get_starred_service),
):
    """Unstar/remove bookmark from an entry."""
    try:
        svc.unstar_entry(entry_id=entry_id, kb_name=kb)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": f"Starred entry '{entry_id}' not found",
            },
        )
    return UnstarEntryResponse(unstarred=True, entry_id=entry_id)


@router.put(
    "/starred/reorder",
    response_model=ReorderStarredResponse,
    dependencies=[Depends(requires_tier("write"))],
)
@limiter.limit("30/minute")
def reorder_starred(
    request: Request,
    body: ReorderStarredRequest,
    svc: StarredService = Depends(get_starred_service),
):
    """Reorder starred entries by updating sort_order values."""
    entries = [item.model_dump() for item in body.entries]
    svc.reorder_starred(entries)
    return ReorderStarredResponse(reordered=True, count=len(body.entries))
