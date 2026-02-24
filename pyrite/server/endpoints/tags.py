"""Tags endpoint."""

from fastapi import APIRouter, Depends, Query, Request

from ...services.kb_service import KBService
from ..api import get_kb_service, limiter, negotiate_response
from ..schemas import TagCount, TagsResponse, TagTreeNode, TagTreeResponse

router = APIRouter(tags=["Tags"])


@router.get("/tags", response_model=TagsResponse)
@limiter.limit("100/minute")
def get_tags(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB"),
    prefix: str | None = Query(None, description="Filter tags by prefix"),
    limit: int = Query(100, ge=1, le=1000),
    svc: KBService = Depends(get_kb_service),
):
    """Get tags with usage counts."""
    tags = svc.get_tags(kb_name=kb, limit=limit)
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


@router.get("/tags/tree", response_model=TagTreeResponse)
@limiter.limit("100/minute")
def get_tag_tree(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB"),
    svc: KBService = Depends(get_kb_service),
):
    """Get hierarchical tag tree."""
    tree = svc.get_tag_tree(kb_name=kb)
    resp_data = {"tree": tree}
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return TagTreeResponse(tree=[TagTreeNode(**node) for node in tree])
