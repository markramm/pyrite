"""Starred/bookmarked entries endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func

from ...storage.database import PyriteDB
from ...storage.models import StarredEntry
from ..api import get_db, limiter, requires_tier
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
    db: PyriteDB = Depends(get_db),
):
    """List all starred entries, optionally filtered by KB."""
    query = db.session.query(StarredEntry)
    if kb:
        query = query.filter(StarredEntry.kb_name == kb)
    query = query.order_by(StarredEntry.sort_order, StarredEntry.created_at.desc())
    results = query.all()

    return StarredEntryListResponse(
        count=len(results),
        starred=[
            StarredEntryItem(
                entry_id=r.entry_id,
                kb_name=r.kb_name,
                sort_order=r.sort_order,
                created_at=r.created_at,
            )
            for r in results
        ],
    )


@router.post("/starred", response_model=StarEntryResponse, dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def star_entry(
    request: Request,
    body: StarEntryRequest,
    db: PyriteDB = Depends(get_db),
):
    """Star/bookmark an entry. Idempotent — starring an already-starred entry succeeds."""
    existing = (
        db.session.query(StarredEntry)
        .filter(
            StarredEntry.entry_id == body.entry_id,
            StarredEntry.kb_name == body.kb_name,
        )
        .first()
    )
    if existing:
        return StarEntryResponse(starred=True, entry_id=body.entry_id, kb_name=body.kb_name)

    max_order = db.session.query(func.max(StarredEntry.sort_order)).scalar() or 0

    starred = StarredEntry(
        entry_id=body.entry_id,
        kb_name=body.kb_name,
        sort_order=max_order + 1,
        created_at=datetime.now(UTC).isoformat(),
    )
    db.session.add(starred)
    db.session.commit()

    return StarEntryResponse(starred=True, entry_id=body.entry_id, kb_name=body.kb_name)


@router.delete("/starred/{entry_id}", response_model=UnstarEntryResponse, dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def unstar_entry(
    request: Request,
    entry_id: str,
    kb: str | None = Query(None, description="KB name"),
    db: PyriteDB = Depends(get_db),
):
    """Unstar/remove bookmark from an entry."""
    query = db.session.query(StarredEntry).filter(StarredEntry.entry_id == entry_id)
    if kb:
        query = query.filter(StarredEntry.kb_name == kb)

    deleted_count = query.delete()
    db.session.commit()

    if deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": f"Starred entry '{entry_id}' not found",
            },
        )

    return UnstarEntryResponse(unstarred=True, entry_id=entry_id)


@router.put("/starred/reorder", response_model=ReorderStarredResponse, dependencies=[Depends(requires_tier("write"))])
@limiter.limit("30/minute")
def reorder_starred(
    request: Request,
    body: ReorderStarredRequest,
    db: PyriteDB = Depends(get_db),
):
    """Reorder starred entries by updating sort_order values."""
    for item in body.entries:
        db.session.query(StarredEntry).filter(
            StarredEntry.entry_id == item.entry_id,
            StarredEntry.kb_name == item.kb_name,
        ).update({"sort_order": item.sort_order})
    db.session.commit()

    return ReorderStarredResponse(reordered=True, count=len(body.entries))
