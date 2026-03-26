"""Filename sanitization utilities."""

import os
import re


def sanitize_filename(entry_id: str) -> str:
    """Sanitize an entry ID for safe use as a filename.

    Strips path separators, parent-directory references, and returns
    only the safe basename.  An empty or all-separator ID is replaced
    with ``_unnamed``.

    Args:
        entry_id: Raw entry ID that may contain path traversal characters.

    Returns:
        A safe filename string with no directory components.
    """
    # Replace path separators with underscores
    safe = entry_id.replace("/", "_").replace("\\", "_")
    # Remove .. components (could appear as standalone or adjacent to underscores)
    safe = re.sub(r"\.\.+", "", safe)
    # Use only the basename (belt-and-suspenders)
    safe = os.path.basename(safe)
    # Strip leading dots to avoid hidden files
    safe = safe.lstrip(".")
    # Collapse runs of underscores
    safe = re.sub(r"_+", "_", safe)
    # Strip leading/trailing underscores
    safe = safe.strip("_")
    # Fallback for empty result
    if not safe:
        safe = "_unnamed"
    return safe
