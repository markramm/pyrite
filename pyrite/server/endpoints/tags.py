"""Tags endpoint."""

from fastapi import APIRouter, Depends, Query, Request

from ...services.kb_service import KBService
from ..api import (
    get_kb_service,
    get_readable_kbs,
    limiter,
    negotiate_response,
    requires_kb_read,
)
from ..schemas import TagCount, TagsResponse, TagTreeNode, TagTreeResponse

router = APIRouter(tags=["Tags"])


@router.get("/tags", response_model=TagsResponse, dependencies=[Depends(requires_kb_read())])
@limiter.limit("100/minute")
def get_tags(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB"),
    prefix: str | None = Query(None, description="Filter tags by prefix"),
    limit: int = Query(100, ge=1, le=1000),
    svc: KBService = Depends(get_kb_service),
    readable: set[str] | None = Depends(get_readable_kbs),
):
    """Get tags with usage counts, over the KBs the caller may read.

    Both the tag *name* and its *count* are KB content: a
    "confidential/operation-zebra (7)" row tells a caller that a KB they
    cannot read exists and how busy it is. So the readable set is pushed
    into the query rather than filtered out of the rows afterwards, which
    would also make ``limit`` and ``count`` wrong.
    """
    tags = svc.get_tags(kb_name=kb, limit=limit, kb_names=None if kb else readable)
    if prefix:
        tags = [t for t in tags if t["name"].startswith(prefix)]

    tag_models = [TagCount(name=t["name"], count=t["count"]) for t in tags]
    resp_data = {
        "count": len(tag_models),
        "tags": [t.model_dump() for t in tag_models],
    }
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return TagsResponse(count=len(tag_models), tags=tag_models)


@router.get(
    "/tags/tree", response_model=TagTreeResponse, dependencies=[Depends(requires_kb_read())]
)
@limiter.limit("100/minute")
def get_tag_tree(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB"),
    svc: KBService = Depends(get_kb_service),
    readable: set[str] | None = Depends(get_readable_kbs),
):
    """Get hierarchical tag tree over the KBs the caller may read."""
    tree = svc.get_tag_tree(kb_name=kb, kb_names=None if kb else readable)
    resp_data = {"tree": tree}
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return TagTreeResponse(tree=[TagTreeNode(**node) for node in tree])
