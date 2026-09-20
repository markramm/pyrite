"""JSON format importer."""

import json
from typing import Any

from ...services.body_bounds import MARKER_KEYS


def import_json(data: str | bytes) -> list[dict[str, Any]]:
    """Parse JSON array of entries.

    Expected format: array of objects with at least {id, title, body}.
    Optional: entry_type, tags, date, importance, sources, links, metadata.

    ADR-0034's truncation keys are carried through when present, so the caller
    can refuse a record whose body is a partial read; this whitelist would
    otherwise strip the marker and hand the importer a body it was told not to
    trust.
    """
    if isinstance(data, bytes):
        data = data.decode("utf-8")

    parsed = json.loads(data)

    if isinstance(parsed, dict):
        # Single entry or wrapped format
        if "entries" in parsed:
            parsed = parsed["entries"]
        else:
            parsed = [parsed]

    entries = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        entry = {
            "id": item.get("id", ""),
            "title": item.get("title", "Untitled"),
            "body": item.get("body", ""),
            "entry_type": item.get("entry_type", item.get("type", "note")),
            "tags": item.get("tags", []),
        }
        # Optional fields
        for key in (
            "date",
            "importance",
            "summary",
            "status",
            "sources",
            "links",
            "metadata",
            *MARKER_KEYS,
        ):
            if key in item:
                entry[key] = item[key]
        entries.append(entry)
    return entries
