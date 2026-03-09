"""Deterministic rubric checker functions for QA evaluation.

Each checker receives an entry dict, optional KBSchema, and optional params dict.
Checkers can be matched by name (NAMED_CHECKERS) or by regex (legacy RUBRIC_CHECKERS).
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

# Type alias for checker functions — params is optional for backward compatibility
RubricChecker = Callable[
    [dict[str, Any], "KBSchema | None", dict[str, Any] | None],
    dict[str, Any] | None,
]

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
# Helper: parse metadata from entry
# =========================================================================


def _parse_metadata(entry: dict[str, Any]) -> dict[str, Any]:
    """Extract metadata dict from entry, handling JSON string or dict."""
    metadata = entry.get("metadata")
    if not metadata:
        return {}
    if isinstance(metadata, str):
        try:
            return json.loads(metadata)
        except (json.JSONDecodeError, ValueError):
            return {}
    if isinstance(metadata, dict):
        return metadata
    return {}


# =========================================================================
# Individual checker functions
# =========================================================================


def check_descriptive_title(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
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
            "rubric_item": (params or {}).get("rubric_text", "Entry has a descriptive title"),
        }
    return None


def check_has_tags(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
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
            "rubric_item": (params or {}).get("rubric_text", "Entry has at least one tag"),
        }
    return None


def check_has_outlinks(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
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
        "rubric_item": (params or {}).get(
            "rubric_text", "Entry links to at least one related entry (unless a stub)"
        ),
    }


def _bind_params(fn: RubricChecker, bound_params: dict[str, Any]) -> RubricChecker:
    """Bind default params to a parameterized checker for use in legacy registry."""

    def wrapper(
        entry: dict[str, Any],
        schema: KBSchema | None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        merged = dict(bound_params)
        if params:
            merged.update(params)
        return fn(entry, schema, merged)

    return wrapper


def check_status_present(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
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
        "rubric_item": (params or {}).get("rubric_text", "status present"),
    }


def check_priority_present(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Check that entry has a priority value."""
    meta_dict = _parse_metadata(entry)
    if meta_dict.get("priority") is not None:
        return None
    return {
        "entry_id": entry["id"],
        "kb_name": entry["kb_name"],
        "rule": "rubric_violation",
        "severity": "warning",
        "field": "metadata.priority",
        "message": f"Entry '{entry['id']}' has no priority",
        "rubric_item": (params or {}).get("rubric_text", "priority present"),
    }




# =========================================================================
# Parameterized checker functions (for named registry, use params at call time)
# =========================================================================


def check_has_field(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Check that a specific metadata field is present. Params: {field: "role"}."""
    if not params or "field" not in params:
        return None
    field_name = params["field"]
    meta_dict = _parse_metadata(entry)
    if meta_dict.get(field_name):
        return None
    return {
        "entry_id": entry["id"],
        "kb_name": entry["kb_name"],
        "rule": "rubric_violation",
        "severity": "warning",
        "field": f"metadata.{field_name}",
        "message": f"Entry '{entry['id']}' is missing '{field_name}' in metadata",
        "rubric_item": params.get("rubric_text", f"{field_name} present"),
    }


def check_has_any_field(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Check that at least one of several metadata fields is present. Params: {fields: ["url", "author"]}."""
    if not params or "fields" not in params:
        return None
    field_names = params["fields"]
    meta_dict = _parse_metadata(entry)
    for fn in field_names:
        if meta_dict.get(fn):
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
        "rubric_item": params.get("rubric_text", f"has {' or '.join(field_names)}"),
    }


def check_body_has_section(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Check that body contains a markdown heading. Params: {heading: "Problem"}."""
    if not params or "heading" not in params:
        return None
    heading = params["heading"]
    body = entry.get("body", "") or ""
    pattern = re.compile(rf"^##\s+{re.escape(heading)}", re.IGNORECASE | re.MULTILINE)
    if pattern.search(body):
        return None
    return {
        "entry_id": entry["id"],
        "kb_name": entry["kb_name"],
        "rule": "rubric_violation",
        "severity": "warning",
        "field": "body",
        "message": f"Entry '{entry['id']}' body missing '## {heading}' section",
        "rubric_item": params.get("rubric_text", f"body has {heading} section"),
    }


def check_body_has_pattern(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Check that body matches a regex pattern. Params: {pattern: "Sources?:"}."""
    if not params or "pattern" not in params:
        return None
    body = entry.get("body", "") or ""
    try:
        compiled = re.compile(params["pattern"], re.IGNORECASE | re.MULTILINE)
    except re.error:
        return None
    if compiled.search(body):
        return None
    return {
        "entry_id": entry["id"],
        "kb_name": entry["kb_name"],
        "rule": "rubric_violation",
        "severity": "warning",
        "field": "body",
        "message": f"Entry '{entry['id']}' body missing expected pattern",
        "rubric_item": params.get("rubric_text", "body matches pattern"),
    }


def check_body_has_code_block(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Check that body contains a code block (```)."""
    body = entry.get("body", "") or ""
    if "```" in body:
        return None
    return {
        "entry_id": entry["id"],
        "kb_name": entry["kb_name"],
        "rule": "rubric_violation",
        "severity": "warning",
        "field": "body",
        "message": f"Entry '{entry['id']}' body has no code block",
        "rubric_item": (params or {}).get("rubric_text", "body contains code block"),
    }


# =========================================================================
# Legacy regex-based registry: (pattern, checker_fn) tuples
# =========================================================================

RUBRIC_CHECKERS: list[tuple[re.Pattern[str], RubricChecker]] = [
    # System-level
    (re.compile(r"descriptive title", re.IGNORECASE), check_descriptive_title),
    (re.compile(r"at least one tag", re.IGNORECASE), check_has_tags),
    (re.compile(r"links to at least one related", re.IGNORECASE), check_has_outlinks),
    # Person type
    (
        re.compile(r"role or position", re.IGNORECASE),
        _bind_params(check_has_field, {"field": "role", "rubric_text": "Person has a role or position described"}),
    ),
    # Document type
    (
        re.compile(r"source URL or author", re.IGNORECASE),
        _bind_params(check_has_any_field, {"fields": ["url", "author"], "rubric_text": "Document has a source URL or author"}),
    ),
    (
        re.compile(r"document_type classification", re.IGNORECASE),
        _bind_params(check_has_field, {"field": "document_type", "rubric_text": "Document has a document_type classification"}),
    ),
    # Component type (KB-level)
    (
        re.compile(r"path present", re.IGNORECASE),
        _bind_params(check_has_field, {"field": "path", "rubric_text": "path present"}),
    ),
    (
        re.compile(r"dependencies present", re.IGNORECASE),
        _bind_params(check_has_field, {"field": "dependencies", "rubric_text": "dependencies present"}),
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
        _bind_params(check_body_has_code_block, {"rubric_text": "body contains code block"}),
    ),
    (
        re.compile(r"section.*Problem|Problem.*section", re.IGNORECASE),
        _bind_params(check_body_has_pattern, {"pattern": r"^##\s+Problem", "rubric_text": "body has Problem section"}),
    ),
    (
        re.compile(r"section.*Alternatives|Alternatives.*section", re.IGNORECASE),
        _bind_params(check_body_has_pattern, {"pattern": r"^##\s+Alternatives", "rubric_text": "body has Alternatives section"}),
    ),
]


# =========================================================================
# Named checker registry
# =========================================================================

NAMED_CHECKERS: dict[str, RubricChecker] = {
    "descriptive_title": check_descriptive_title,
    "has_tags": check_has_tags,
    "has_outlinks": check_has_outlinks,
    "status_present": check_status_present,
    "priority_present": check_priority_present,
    "has_field": check_has_field,
    "has_any_field": check_has_any_field,
    "body_has_section": check_body_has_section,
    "body_has_pattern": check_body_has_pattern,
    "body_has_code_block": check_body_has_code_block,
}


def match_rubric_item(item: str) -> RubricChecker | None:
    """Return the checker function for a rubric item, or None if no match."""
    for pattern, checker in RUBRIC_CHECKERS:
        if pattern.search(item):
            return checker
    return None
