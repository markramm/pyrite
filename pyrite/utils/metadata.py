"""Metadata parsing utilities."""

import json
from typing import Any


def parse_metadata(raw: Any) -> dict[str, Any]:
    """Parse metadata that may be a JSON string, dict, or None.

    Returns an empty dict for any unparseable input.
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}
