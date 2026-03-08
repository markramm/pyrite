"""Deterministic rubric checker functions for QA evaluation.

Each checker receives an entry dict and optional KBSchema, returns an issue dict or None.
Checkers are matched to rubric item text via regex patterns.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..schema import KBSchema

logger = logging.getLogger(__name__)

# Type alias for checker functions
RubricChecker = Callable[[dict[str, Any], "KBSchema | None"], dict[str, Any] | None]

# =========================================================================
# Generic title blocklist
# =========================================================================

GENERIC_TITLES = frozenset({
    "update",
    "notes",
    "todo",
    "untitled",
    "new entry",
    "draft",
    "temp",
    "test",
    "placeholder",
    "wip",
})

# =========================================================================
# Patterns for rubric items already covered by existing QA rules
# =========================================================================

ALREADY_COVERED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"body is non-empty", re.IGNORECASE),
    re.compile(r"has a date field", re.IGNORECASE),
    re.compile(r"importance.*between", re.IGNORECASE),
]


def is_already_covered(rubric_item: str) -> bool:
    """Check if a rubric item is already covered by existing QA rules."""
    return any(p.search(rubric_item) for p in ALREADY_COVERED_PATTERNS)


# =========================================================================
# Individual checker functions
# =========================================================================


def check_descriptive_title(entry: dict[str, Any], schema: KBSchema | None) -> dict[str, Any] | None:
    """Check that entry has a descriptive (non-generic) title."""
    title = entry.get("title", "") or ""
    if title.strip().lower() in GENERIC_TITLES:
        return {
            "entry_id": entry["id"],
            "kb_name": entry["kb_name"],
            "rule": "rubric_violation",
            "severity": "warning",
            "field": "title",
            "message": f"Entry '{entry['id']}' has a generic title: '{title}'",
            "rubric_item": "Entry has a descriptive title",
        }
    return None


def check_has_tags(entry: dict[str, Any], schema: KBSchema | None) -> dict[str, Any] | None:
    """Check that entry has at least one tag."""
    tag_count = entry.get("_tag_count", 0)
    if tag_count == 0:
        return {
            "entry_id": entry["id"],
            "kb_name": entry["kb_name"],
            "rule": "rubric_violation",
            "severity": "warning",
            "field": "tags",
            "message": f"Entry '{entry['id']}' has no tags",
            "rubric_item": "Entry has at least one tag",
        }
    return None


def check_has_outlinks(entry: dict[str, Any], schema: KBSchema | None) -> dict[str, Any] | None:
    """Check that entry links to at least one related entry (unless a stub)."""
    link_count = entry.get("_outlink_count", 0)
    if link_count > 0:
        return None

    # Check for stub marker in body
    body = entry.get("body", "") or ""
    if "stub" in body.lower():
        return None

    return {
        "entry_id": entry["id"],
        "kb_name": entry["kb_name"],
        "rule": "rubric_violation",
        "severity": "warning",
        "field": "links",
        "message": f"Entry '{entry['id']}' has no outgoing links",
        "rubric_item": "Entry links to at least one related entry (unless a stub)",
    }


def _make_metadata_field_checker(
    field_name: str, rubric_text: str
) -> RubricChecker:
    """Factory: create a checker that verifies a metadata JSON field is present."""

    def checker(entry: dict[str, Any], schema: KBSchema | None) -> dict[str, Any] | None:
        metadata = entry.get("metadata")
        meta_dict: dict[str, Any] = {}
        if metadata:
            if isinstance(metadata, str):
                try:
                    meta_dict = json.loads(metadata)
                except (json.JSONDecodeError, ValueError):
                    pass
            elif isinstance(metadata, dict):
                meta_dict = metadata

        if meta_dict.get(field_name):
            return None

        return {
            "entry_id": entry["id"],
            "kb_name": entry["kb_name"],
            "rule": "rubric_violation",
            "severity": "warning",
            "field": f"metadata.{field_name}",
            "message": f"Entry '{entry['id']}' is missing '{field_name}' in metadata",
            "rubric_item": rubric_text,
        }

    return checker


def _make_metadata_any_field_checker(
    field_names: list[str], rubric_text: str
) -> RubricChecker:
    """Factory: check that at least one of several metadata fields is present."""

    def checker(entry: dict[str, Any], schema: KBSchema | None) -> dict[str, Any] | None:
        metadata = entry.get("metadata")
        meta_dict: dict[str, Any] = {}
        if metadata:
            if isinstance(metadata, str):
                try:
                    meta_dict = json.loads(metadata)
                except (json.JSONDecodeError, ValueError):
                    pass
            elif isinstance(metadata, dict):
                meta_dict = metadata

        for field_name in field_names:
            if meta_dict.get(field_name):
                return None

        return {
            "entry_id": entry["id"],
            "kb_name": entry["kb_name"],
            "rule": "rubric_violation",
            "severity": "warning",
            "field": "metadata",
            "message": (
                f"Entry '{entry['id']}' is missing "
                f"{' or '.join(field_names)} in metadata"
            ),
            "rubric_item": rubric_text,
        }

    return checker


def check_status_present(entry: dict[str, Any], schema: KBSchema | None) -> dict[str, Any] | None:
    """Check that entry has a status value."""
    if entry.get("status"):
        return None
    return {
        "entry_id": entry["id"],
        "kb_name": entry["kb_name"],
        "rule": "rubric_violation",
        "severity": "warning",
        "field": "status",
        "message": f"Entry '{entry['id']}' has no status",
        "rubric_item": "status present",
    }


def check_priority_present(entry: dict[str, Any], schema: KBSchema | None) -> dict[str, Any] | None:
    """Check that entry has a priority value."""
    metadata = entry.get("metadata")
    meta_dict: dict[str, Any] = {}
    if metadata:
        if isinstance(metadata, str):
            try:
                meta_dict = json.loads(metadata)
            except (json.JSONDecodeError, ValueError):
                pass
        elif isinstance(metadata, dict):
            meta_dict = metadata

    if meta_dict.get("priority") is not None:
        return None
    return {
        "entry_id": entry["id"],
        "kb_name": entry["kb_name"],
        "rule": "rubric_violation",
        "severity": "warning",
        "field": "metadata.priority",
        "message": f"Entry '{entry['id']}' has no priority",
        "rubric_item": "priority present",
    }


def _make_body_section_checker(
    section_pattern: str, rubric_text: str
) -> RubricChecker:
    """Factory: check that body contains a section heading or pattern."""
    compiled = re.compile(section_pattern, re.IGNORECASE | re.MULTILINE)

    def checker(entry: dict[str, Any], schema: KBSchema | None) -> dict[str, Any] | None:
        body = entry.get("body", "") or ""
        if compiled.search(body):
            return None
        return {
            "entry_id": entry["id"],
            "kb_name": entry["kb_name"],
            "rule": "rubric_violation",
            "severity": "warning",
            "field": "body",
            "message": f"Entry '{entry['id']}' body missing expected section/pattern",
            "rubric_item": rubric_text,
        }

    return checker


def _make_body_has_code_block_checker(rubric_text: str) -> RubricChecker:
    """Factory: check that body contains a code block."""
    return _make_body_section_checker(r"```", rubric_text)


# =========================================================================
# Rubric checker registry: (pattern, checker_fn) tuples
# =========================================================================

# System-level rubric checkers
RUBRIC_CHECKERS: list[tuple[re.Pattern[str], RubricChecker]] = [
    # System-level
    (re.compile(r"descriptive title", re.IGNORECASE), check_descriptive_title),
    (re.compile(r"at least one tag", re.IGNORECASE), check_has_tags),
    (re.compile(r"links to at least one related", re.IGNORECASE), check_has_outlinks),
    # Person type
    (
        re.compile(r"role or position", re.IGNORECASE),
        _make_metadata_field_checker("role", "Person has a role or position described"),
    ),
    # Document type
    (
        re.compile(r"source URL or author", re.IGNORECASE),
        _make_metadata_any_field_checker(
            ["url", "author"], "Document has a source URL or author"
        ),
    ),
    (
        re.compile(r"document_type classification", re.IGNORECASE),
        _make_metadata_field_checker(
            "document_type", "Document has a document_type classification"
        ),
    ),
    # Component type (KB-level)
    (
        re.compile(r"path present", re.IGNORECASE),
        _make_metadata_field_checker("path", "path present"),
    ),
    (
        re.compile(r"dependencies present", re.IGNORECASE),
        _make_metadata_field_checker("dependencies", "dependencies present"),
    ),
    # ADR/backlog_item status
    (
        re.compile(r"status.*valid set|status present", re.IGNORECASE),
        check_status_present,
    ),
    # Priority
    (
        re.compile(r"priority present", re.IGNORECASE),
        check_priority_present,
    ),
    # Body structure checks
    (
        re.compile(r"body.*code block|contains.*code block", re.IGNORECASE),
        _make_body_has_code_block_checker("body contains code block"),
    ),
    (
        re.compile(r"section.*Problem|Problem.*section", re.IGNORECASE),
        _make_body_section_checker(r"^##\s+Problem", "body has Problem section"),
    ),
    (
        re.compile(r"section.*Alternatives|Alternatives.*section", re.IGNORECASE),
        _make_body_section_checker(r"^##\s+Alternatives", "body has Alternatives section"),
    ),
]


def match_rubric_item(item: str) -> RubricChecker | None:
    """Return the checker function for a rubric item, or None if no match."""
    for pattern, checker in RUBRIC_CHECKERS:
        if pattern.search(item):
            return checker
    return None
