"""CSV format importer."""

import csv
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)


def import_csv(data: str | bytes) -> list[dict[str, Any]]:
    """Parse CSV with header row mapping to entry fields.

    Required columns: title
    Optional columns: id, body, entry_type/type, tags, date, importance, summary
    Tags can be semicolon-separated within the column.
    """
    if isinstance(data, bytes):
        data = data.decode("utf-8")

    reader = csv.DictReader(io.StringIO(data))
    entries = []

    for row in reader:
        entry: dict[str, Any] = {
            "id": row.get("id", ""),
            "title": row.get("title", "Untitled"),
            "body": row.get("body", ""),
            "entry_type": row.get("entry_type", row.get("type", "note")),
        }

        # Parse tags (semicolon-separated)
        tags_str = row.get("tags", "")
        entry["tags"] = [t.strip() for t in tags_str.split(";") if t.strip()] if tags_str else []

        # Optional fields
        if row.get("date"):
            entry["date"] = row["date"]
        if row.get("importance"):
            try:
                entry["importance"] = int(row["importance"])
            except (ValueError, TypeError):
                logger.debug("Could not parse importance value: %s", row["importance"])
        if row.get("summary"):
            entry["summary"] = row["summary"]

        entries.append(entry)

    return entries
