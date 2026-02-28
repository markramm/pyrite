"""Entry factory -- single point of entry type dispatch."""

from ..schema import generate_entry_id
from .base import Entry
from .collection import CollectionEntry
from .core_types import (
    ENTRY_TYPE_REGISTRY,
    EventEntry,
    OrganizationEntry,
    PersonEntry,
    get_entry_class,
)
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

    Handles type-specific fields (date for events, role for persons, etc.),
    core registry types, plugin-provided types, and GenericEntry fallback.

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

    if entry_type == "event":
        return EventEntry(
            id=entry_id,
            title=title,
            body=body,
            date=kwargs.get("date", ""),
            importance=kwargs.get("importance", 5),
            location=kwargs.get("location", ""),
            status=kwargs.get("status", "confirmed"),
            participants=kwargs.get("participants", []),
            tags=kwargs.get("tags", []),
            summary=kwargs.get("summary", ""),
            metadata=kwargs.get("metadata", {}),
        )
    elif entry_type == "person":
        return PersonEntry(
            id=entry_id,
            title=title,
            body=body,
            role=kwargs.get("role", ""),
            importance=kwargs.get("importance", 5),
            tags=kwargs.get("tags", []),
            summary=kwargs.get("summary", ""),
            metadata=kwargs.get("metadata", {}),
        )
    elif entry_type == "organization":
        return OrganizationEntry(
            id=entry_id,
            title=title,
            body=body,
            importance=kwargs.get("importance", 5),
            tags=kwargs.get("tags", []),
            summary=kwargs.get("summary", ""),
            metadata=kwargs.get("metadata", {}),
        )
    elif entry_type == "collection":
        return CollectionEntry(
            id=entry_id,
            title=title,
            body=body,
            source_type=kwargs.get("source_type", "folder"),
            description=kwargs.get("description", ""),
            icon=kwargs.get("icon", ""),
            view_config=kwargs.get("view_config", {"default_view": "list"}),
            entry_filter=kwargs.get("entry_filter", {}),
            folder_path=kwargs.get("folder_path", ""),
            tags=kwargs.get("tags", []),
            summary=kwargs.get("summary", ""),
            metadata=kwargs.get("metadata", {}),
        )
    elif entry_type in ENTRY_TYPE_REGISTRY:
        cls = ENTRY_TYPE_REGISTRY[entry_type]
        # Capture non-standard kwargs as metadata so --field / frontmatter extras persist
        _known = {"tags", "summary", "metadata", "date", "importance"}
        _extra_meta = {k: v for k, v in kwargs.items() if k not in _known}
        _metadata = {**kwargs.get("metadata", {}), **_extra_meta}
        return cls(
            id=entry_id,
            title=title,
            body=body,
            tags=kwargs.get("tags", []),
            summary=kwargs.get("summary", ""),
            metadata=_metadata,
        )
    else:
        # Check plugin registry, then fall back to GenericEntry
        resolved_cls = get_entry_class(entry_type)
        if resolved_cls is not GenericEntry:
            # Build frontmatter from all kwargs — plugin entry types expect
            # their fields (date, importance, actors, etc.) as top-level keys.
            # Unknown kwargs are collected into the metadata dict so they
            # persist through from_frontmatter() round-trips.
            import dataclasses as _dc

            _cls_fields = {f.name for f in _dc.fields(resolved_cls)}
            # Keys recognised as top-level frontmatter by from_frontmatter
            _fm_keys = _cls_fields | {
                "type", "provenance", "sources", "links", "aliases",
                "created_at", "updated_at",
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
        else:
            return GenericEntry(
                id=entry_id,
                title=title,
                body=body,
                _entry_type=entry_type,
                tags=kwargs.get("tags", []),
                summary=kwargs.get("summary", ""),
                metadata=kwargs.get("metadata", {}),
            )
