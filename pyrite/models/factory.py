"""Entry factory -- single point of entry type dispatch."""

import dataclasses as _dc

from ..schema import generate_entry_id
from .base import Entry
from .core_types import get_entry_class
from .generic import GenericEntry


def build_entry(
    entry_type: str,
    *,
    entry_id: str | None = None,
    title: str,
    body: str = "",
    **kwargs,
) -> Entry:
    """Build an entry of the given type with appropriate constructor kwargs.

    All types (core, plugin, unknown) are resolved through the type registry
    and constructed via ``from_frontmatter()``.  Unknown types fall back to
    ``GenericEntry``.

    Args:
        entry_type: The entry type string (e.g., "event", "person", "note")
        entry_id: Optional entry ID. Auto-generated from title if not provided.
        title: Entry title (required)
        body: Entry body content
        **kwargs: Type-specific fields (date, importance, role, participants, etc.)

    Returns:
        An Entry instance of the appropriate type
    """
    if entry_id is None:
        entry_id = generate_entry_id(title)

    resolved_cls = get_entry_class(entry_type)

    if resolved_cls is GenericEntry:
        return GenericEntry(
            id=entry_id,
            title=title,
            body=body,
            _entry_type=entry_type,
            tags=kwargs.get("tags", []),
            summary=kwargs.get("summary", ""),
            metadata=kwargs.get("metadata", {}),
        )

    # Build frontmatter dict for from_frontmatter().
    # Known dataclass fields go as top-level keys; unknown kwargs are
    # collected into metadata so they persist through round-trips.
    _cls_fields = {f.name for f in _dc.fields(resolved_cls)}
    _fm_keys = _cls_fields | {
        "type",
        "provenance",
        "sources",
        "links",
        "aliases",
        "created_at",
        "updated_at",
    }

    fm: dict = {
        "id": entry_id,
        "title": title,
        "type": entry_type,
    }
    _extra_meta: dict = {}
    for k, v in kwargs.items():
        if k == "metadata" or k in _fm_keys:
            fm[k] = v
        else:
            _extra_meta[k] = v

    # Merge unknown kwargs into metadata so they survive round-trip
    if _extra_meta:
        existing = fm.get("metadata") or {}
        fm["metadata"] = {**existing, **_extra_meta}

    return resolved_cls.from_frontmatter(fm, body)
