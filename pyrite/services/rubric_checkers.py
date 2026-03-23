"""Deterministic rubric checker functions for QA evaluation.

Each checker receives an entry dict, optional KBSchema, and optional params dict.
Checkers are matched by name via the NAMED_CHECKERS registry.
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

GENERIC_TITLES = frozenset(
    {
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
    }
)


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
        "message": (f"Entry '{entry['id']}' is missing {' or '.join(field_names)} in metadata"),
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


def check_not_oversized(
    entry: dict[str, Any],
    schema: KBSchema | None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Fail if effort is XL or larger and item has no subtask links."""
    meta = _parse_metadata(entry)
    effort = meta.get("effort", "")
    oversized = {"XL", "XXL", "xl", "xxl"}
    if effort in oversized:
        # Pass if the item has has_subtask links (decomposed into subtasks)
        links = entry.get("_links", [])
        has_subtasks = any(
            (isinstance(lnk, dict) and lnk.get("relation") == "has_subtask") for lnk in links
        )
        if has_subtasks:
            return None
        return {
            "entry_id": entry["id"],
            "kb_name": entry["kb_name"],
            "rule": "rubric_violation",
            "severity": "warning",
            "field": "metadata.effort",
            "message": f"Item effort is {effort} — consider decomposing into subtasks",
            "rubric_item": (params or {}).get("rubric_text", "not oversized"),
        }
    return None


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
    "not_oversized": check_not_oversized,
}
