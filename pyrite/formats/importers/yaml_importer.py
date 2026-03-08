"""YAML format importer."""

from typing import Any

from pyrite.utils.yaml import load_yaml


def import_yaml(data: str | bytes) -> list[dict[str, Any]]:
    """Parse YAML array of entries.

    Expected format: array of objects with at least {title, body}.
    Accepts {"entries": [...]} wrapper or bare list.
    """
    if isinstance(data, bytes):
        data = data.decode("utf-8")

    parsed = load_yaml(data)

    if isinstance(parsed, dict):
        if "entries" in parsed:
            parsed = parsed["entries"]
        else:
            parsed = [parsed]

    if not isinstance(parsed, list):
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
        for key in ("date", "importance", "summary", "status", "sources", "links", "metadata"):
            if key in item:
                entry[key] = item[key]
        entries.append(entry)
    return entries
