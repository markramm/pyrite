"""Encyclopedia validation rules."""

from typing import Any

from .entry_types import PROTECTION_LEVELS, QUALITY_LEVELS, REVIEW_STATUSES


def validate_encyclopedia(
    entry_type: str, data: dict[str, Any], context: dict[str, Any]
) -> list[dict]:
    """Validate encyclopedia-specific rules."""
    errors: list[dict] = []

    if entry_type == "article":
        # Validate enum values
        quality = data.get("quality", "stub")
        if quality not in QUALITY_LEVELS:
            errors.append(
                {
                    "field": "quality",
                    "rule": "enum",
                    "expected": list(QUALITY_LEVELS),
                    "got": quality,
                }
            )

        review_status = data.get("review_status", "draft")
        if review_status not in REVIEW_STATUSES:
            errors.append(
                {
                    "field": "review_status",
                    "rule": "enum",
                    "expected": list(REVIEW_STATUSES),
                    "got": review_status,
                }
            )

        protection = data.get("protection_level", "none")
        if protection not in PROTECTION_LEVELS:
            errors.append(
                {
                    "field": "protection_level",
                    "rule": "enum",
                    "expected": list(PROTECTION_LEVELS),
                    "got": protection,
                }
            )

        # Articles with quality >= GA must have at least 3 sources
        if quality in ("GA", "FA"):
            sources = data.get("sources", [])
            if len(sources) < 3:
                errors.append(
                    {
                        "field": "sources",
                        "rule": "ga_min_sources",
                        "expected": "at least 3 sources for GA/FA articles",
                        "got": len(sources),
                    }
                )

        # Articles with quality >= B must have non-empty body (>500 chars)
        if quality in ("B", "GA", "FA"):
            body = data.get("body", "")
            if len(body) < 500:
                errors.append(
                    {
                        "field": "body",
                        "rule": "b_min_length",
                        "expected": "body >= 500 characters for B+ quality",
                        "got": len(body),
                    }
                )

        # Published articles must have passed review
        # (this is a warning — the workflow enforces the hard constraint)
        if review_status == "published" and quality == "stub":
            errors.append(
                {
                    "field": "quality",
                    "rule": "published_not_stub",
                    "expected": "published articles should be at least 'start' quality",
                    "got": quality,
                    "severity": "warning",
                }
            )

        # Categories should be non-empty for non-stubs (warning)
        if quality not in ("stub",) and not data.get("categories"):
            errors.append(
                {
                    "field": "categories",
                    "rule": "categories_recommended",
                    "expected": "at least 1 category for non-stub articles",
                    "got": 0,
                    "severity": "warning",
                }
            )

    elif entry_type == "talk_page":
        # Talk pages must reference an article
        if not data.get("article_id"):
            errors.append(
                {
                    "field": "article_id",
                    "rule": "required",
                    "expected": "non-empty article_id for talk pages",
                    "got": data.get("article_id"),
                }
            )

    return errors
