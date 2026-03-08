"""QA review operations.

Mixin class for review-related data access.
"""

from datetime import UTC, datetime
from typing import Any

from .models import Review


class ReviewOpsMixin:
    """Create, query, and delete QA reviews for KB entries."""

    def create_review(
        self,
        entry_id: str,
        kb_name: str,
        content_hash: str,
        reviewer: str,
        reviewer_type: str,
        result: str,
        details: str | None = None,
    ) -> dict[str, Any]:
        """Insert a new review. Returns review dict."""
        now = datetime.now(UTC).isoformat()
        review = Review(
            entry_id=entry_id,
            kb_name=kb_name,
            content_hash=content_hash,
            reviewer=reviewer,
            reviewer_type=reviewer_type,
            result=result,
            details=details,
            created_at=now,
        )
        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)
        return self._review_to_dict(review)

    def get_reviews(
        self, entry_id: str, kb_name: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get reviews for an entry, newest first."""
        reviews = (
            self.session.query(Review)
            .filter_by(entry_id=entry_id, kb_name=kb_name)
            .order_by(Review.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._review_to_dict(r) for r in reviews]

    def get_latest_review(
        self, entry_id: str, kb_name: str
    ) -> dict[str, Any] | None:
        """Get the most recent review for an entry."""
        review = (
            self.session.query(Review)
            .filter_by(entry_id=entry_id, kb_name=kb_name)
            .order_by(Review.created_at.desc())
            .first()
        )
        return self._review_to_dict(review) if review else None

    def delete_review(self, review_id: int) -> bool:
        """Delete a review by ID. Returns True if deleted."""
        count = self.session.query(Review).filter_by(id=review_id).delete()
        self.session.commit()
        return count > 0

    def _review_to_dict(self, review: Review) -> dict[str, Any]:
        """Convert Review ORM object to dict."""
        return {
            "id": review.id,
            "entry_id": review.entry_id,
            "kb_name": review.kb_name,
            "content_hash": review.content_hash,
            "reviewer": review.reviewer,
            "reviewer_type": review.reviewer_type,
            "result": review.result,
            "details": review.details,
            "created_at": review.created_at,
        }
