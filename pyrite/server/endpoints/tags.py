"""Tags endpoint."""

from fastapi import APIRouter, Depends, Query, Request

from ...services.kb_service import KBService
from ..api import get_kb_service, limiter, negotiate_response
from ..schemas import TagCount, TagsResponse

router = APIRouter(tags=["Tags"])


@router.get("/tags", response_model=TagsResponse)
@limiter.limit("100/minute")
def get_tags(
    request: Request,
    kb: str | None = Query(None, description="Filter by KB"),
    limit: int = Query(100, ge=1, le=1000),
    svc: KBService = Depends(get_kb_service),
):
    """Get tags with usage counts."""
    tags = svc.get_tags(kb_name=kb, limit=limit)

    tag_models = [TagCount(name=t["name"], count=t["count"]) for t in tags]
    resp_data = {
        "count": len(tags),
        "tags": [t.model_dump() for t in tag_models],
    }
    neg = negotiate_response(request, resp_data)
    if neg is not None:
        return neg
    return TagsResponse(count=len(tags), tags=tag_models)
