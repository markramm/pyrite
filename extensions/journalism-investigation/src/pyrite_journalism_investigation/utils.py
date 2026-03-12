"""Shared utilities for journalism-investigation plugin."""

import json
from typing import Any


def parse_meta(entry_dict: dict[str, Any]) -> dict[str, Any]:
    """Parse metadata from a DB entry dict, handling JSON strings."""
    meta = entry_dict.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            meta = {}
    return meta


def strip_wikilink(ref: str) -> str:
    """Extract entry ID from a wikilink reference like [[some-id]]."""
    return ref.strip().strip("[]").replace("[[", "").replace("]]", "")
