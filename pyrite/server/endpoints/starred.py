"""Starred/bookmarked entries endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...exceptions import EntryNotFoundError
from ...services.access_policy import KB, Action, ReadScope
from ...services.starred_service import INSTANCE_USER, StarredService
from ..api import (
    get_starred_service,
    limiter,
    requires_tier,
)
from ..authz import authorize
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


def _star_owner(request: Request) -> int | None:
    """Whose star list this request reads and changes.

    A logged-in user: their own. A caller with no user identity -- auth
    disabled, or an operator API key -- the instance's list. An anonymous
    visitor on an auth-enabled instance has no list (None): letting them
    share the instance's would put every visitor's stars in one list again.
    """
    auth_user = getattr(request.state, "auth_user", None)
    if auth_user:
        return auth_user["id"]
    if getattr(request.state, "anonymous", False):
        return None
    return INSTANCE_USER


def _require_star_owner(request: Request) -> int:
    owner = _star_owner(request)
    if owner is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "LOGIN_REQUIRED", "message": "Sign in to star entries"},
        )
    return owner


@router.get("/starred", response_model=StarredEntryListResponse)
@limiter.limit("100/minute")
def list_starred(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB name"),
    svc: StarredService = Depends(get_starred_service),
    scope: ReadScope = Depends(authorize(Action.KB_READ, KB)),
):
    """List the caller's starred entries in the KBs they may read.

    A star resolves its entry's *title* from the backend, so an
    unfiltered list hands over private titles; the filter therefore goes
    into the query, before titles are resolved.
    """
    owner = _star_owner(request)
    if owner is None:
        return StarredEntryListResponse(count=0, starred=[])
    items = svc.list_starred(owner, kb=kb, kb_names=None if kb else scope.as_set())
    return StarredEntryListResponse(
        count=len(items),
        starred=[StarredEntryItem(**item) for item in items],
    )


@router.post(
    "/starred",
    response_model=StarEntryResponse,
    dependencies=[Depends(requires_tier("write")), Depends(authorize(Action.KB_READ, KB))],
)
@limiter.limit("30/minute")
def star_entry(
    request: Request,
    body: StarEntryRequest,
    svc: StarredService = Depends(get_starred_service),
):
    """Star/bookmark an entry in the caller's own list. Idempotent — starring an
    already-starred entry succeeds. A KB the caller cannot read answers 404."""
    owner = _require_star_owner(request)
    result = svc.star_entry(owner, entry_id=body.entry_id, kb_name=body.kb_name)
    return StarEntryResponse(**result)


@router.delete(
    "/starred/{entry_id}",
    response_model=UnstarEntryResponse,
    dependencies=[Depends(requires_tier("write")), Depends(authorize(Action.KB_READ, KB))],
)
@limiter.limit("30/minute")
def unstar_entry(
    request: Request,
    entry_id: str,
    kb: str | None = Query(None, description="KB name"),
    svc: StarredService = Depends(get_starred_service),
):
    """Unstar an entry in the caller's own list; another user's star is 404."""
    owner = _require_star_owner(request)
    try:
        svc.unstar_entry(owner, entry_id=entry_id, kb_name=kb)
    except EntryNotFoundError:
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
    """Reorder the caller's own starred entries; items naming anyone else's
    stars change nothing."""
    owner = _require_star_owner(request)
    entries = [item.model_dump() for item in body.entries]
    svc.reorder_starred(owner, entries)
    return ReorderStarredResponse(reordered=True, count=len(body.entries))
