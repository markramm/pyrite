"""QA review endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ...services.kb_service import KBService
from ..api import get_kb_service, limiter, requires_kb_tier

router = APIRouter(tags=["Reviews"])


# -- Request / Response models ------------------------------------------------


class CreateReviewRequest(BaseModel):
    entry_id: str
    kb_name: str
    reviewer: str
    reviewer_type: str  # "user" or "agent"
    result: str  # "pass", "fail", "partial"
    details: str | None = None


class ReviewResponse(BaseModel):
    id: int
    entry_id: str
    kb_name: str
    content_hash: str
    reviewer: str
    reviewer_type: str
    result: str
    details: str | None = None
    created_at: str | None = None


class ReviewListResponse(BaseModel):
    count: int
    reviews: list[ReviewResponse]


class ReviewStatusResponse(BaseModel):
    current: bool
    review: ReviewResponse | None = None


# -- Endpoints -----------------------------------------------------------------


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    dependencies=[Depends(requires_kb_tier("write"))],
)
@limiter.limit("30/minute")
def create_review(
    request: Request,
    body: CreateReviewRequest,
    svc: KBService = Depends(get_kb_service),
):
    """Create a QA review for an entry."""
    if body.reviewer_type not in ("user", "agent"):
        raise HTTPException(status_code=422, detail="reviewer_type must be 'user' or 'agent'")
    if body.result not in ("pass", "fail", "partial"):
        raise HTTPException(status_code=422, detail="result must be 'pass', 'fail', or 'partial'")
    try:
        review = svc.create_review(
            entry_id=body.entry_id,
            kb_name=body.kb_name,
            reviewer=body.reviewer,
            reviewer_type=body.reviewer_type,
            result=body.result,
            details=body.details,
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ReviewResponse(**review)


@router.get("/reviews", response_model=ReviewListResponse)
@limiter.limit("100/minute")
def list_reviews(
    request: Request,
    entry_id: str = Query(..., description="Entry ID"),
    kb: str = Query(..., alias="kb_name", description="KB name"),
    limit: int = Query(50, ge=1, le=200),
    svc: KBService = Depends(get_kb_service),
):
    """List reviews for an entry."""
    reviews = svc.get_reviews(entry_id, kb, limit=limit)
    return ReviewListResponse(
        count=len(reviews),
        reviews=[ReviewResponse(**r) for r in reviews],
    )


@router.get("/reviews/latest", response_model=ReviewResponse)
@limiter.limit("100/minute")
def get_latest_review(
    request: Request,
    entry_id: str = Query(..., description="Entry ID"),
    kb: str = Query(..., alias="kb_name", description="KB name"),
    svc: KBService = Depends(get_kb_service),
):
    """Get the latest review for an entry."""
    review = svc.get_latest_review(entry_id, kb)
    if not review:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "No reviews found"},
        )
    return ReviewResponse(**review)


@router.get("/reviews/status", response_model=ReviewStatusResponse)
@limiter.limit("100/minute")
def get_review_status(
    request: Request,
    entry_id: str = Query(..., description="Entry ID"),
    kb: str = Query(..., alias="kb_name", description="KB name"),
    svc: KBService = Depends(get_kb_service),
):
    """Check if the latest review is still current (file unchanged since review)."""
    status = svc.is_review_current(entry_id, kb)
    review = status["review"]
    return ReviewStatusResponse(
        current=status["current"],
        review=ReviewResponse(**review) if review else None,
    )


@router.delete(
    "/reviews/{review_id}",
    dependencies=[Depends(requires_kb_tier("write"))],
)
@limiter.limit("30/minute")
def delete_review(
    request: Request,
    review_id: int,
    svc: KBService = Depends(get_kb_service),
):
    """Delete a review."""
    deleted = svc.db.delete_review(review_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Review {review_id} not found"},
        )
    return {"deleted": True, "review_id": review_id}
