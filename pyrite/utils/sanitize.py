"""Filename sanitization utilities."""

import hashlib
import os
import re

# Length of the sha256-derived disambiguation suffix appended by
# unique_path_component() for values that sanitize_filename() had to change.
_HASH_SUFFIX_LEN = 8


def sanitize_filename(entry_id: str) -> str:
    """Sanitize an entry ID for safe use as a filename.

    Strips path separators, parent-directory references, and returns
    only the safe basename.  An empty or all-separator ID is replaced
    with ``_unnamed``.

    Note: this does not handle Windows drive-relative forms (e.g. ``C:foo``)
    -- Windows is not a supported deployment target today, so a value like
    that is not guaranteed to have no directory components once interpreted
    by a Windows path API.

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
    # Strip trailing underscores (preserve leading _ for special entries like _about, _homepage)
    safe = safe.rstrip("_")
    # Fallback for empty result
    if not safe:
        safe = "_unnamed"
    return safe


def unique_path_component(raw: str) -> str:
    """Sanitize `raw` into a path component, collision-free across distinct inputs.

    sanitize_filename() alone can make two distinct raw values collide (e.g.
    "note_", "note/" and "note.." all sanitize to "note", the same as the
    already-safe raw value "note" itself) -- a later entry then silently
    overwrites an earlier one's export output (#221 redispatch).

    The rule: a value that sanitize_filename() leaves unchanged ("safe") keeps
    exactly that name, so every existing export's filenames are unaffected.
    A value sanitize_filename() had to change ("unsafe") gets a short suffix
    derived from a hash of the raw value, so it can never collide with either
    a safe value's name or another unsafe value's sanitized form:

        -<first 8 hex chars of sha256(raw)>

    This is deterministic (same raw -> same output, useful for idempotent
    re-exports) and collision-free without needing to track what other names
    have already been produced in this export.

    Args:
        raw: Raw, caller-controlled value (an entry id or entry_type).

    Returns:
        A safe path component with no directory components.
    """
    safe = sanitize_filename(raw)
    if safe == raw:
        return safe
    suffix = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:_HASH_SUFFIX_LEN]
    return f"{safe}-{suffix}"
