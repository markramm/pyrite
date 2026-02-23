"""Social KB validation rules."""

from typing import Any

from .entry_types import WRITEUP_TYPES


def validate_social(entry_type: str, data: dict[str, Any], context: dict[str, Any]) -> list[dict]:
    """Validate social KB-specific rules."""
    errors: list[dict] = []

    if entry_type == "writeup":
        # Writeups must have an author_id
        if not data.get("author_id"):
            errors.append(
                {
                    "field": "author_id",
                    "rule": "required",
                    "expected": "non-empty author_id for writeups",
                    "got": data.get("author_id"),
                }
            )

        # Writeup type must be valid
        writeup_type = data.get("writeup_type", "essay")
        if writeup_type not in WRITEUP_TYPES:
            errors.append(
                {
                    "field": "writeup_type",
                    "rule": "enum",
                    "expected": list(WRITEUP_TYPES),
                    "got": writeup_type,
                }
            )

    return errors
