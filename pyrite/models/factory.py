"""Entry factory -- single point of entry type dispatch."""

from ..schema import generate_entry_id
from .base import Entry
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
        )
    elif entry_type == "organization":
        return OrganizationEntry(
            id=entry_id,
            title=title,
            body=body,
            importance=kwargs.get("importance", 5),
            tags=kwargs.get("tags", []),
            summary=kwargs.get("summary", ""),
        )
    elif entry_type in ENTRY_TYPE_REGISTRY:
        cls = ENTRY_TYPE_REGISTRY[entry_type]
        return cls(
            id=entry_id,
            title=title,
            body=body,
            tags=kwargs.get("tags", []),
            summary=kwargs.get("summary", ""),
        )
    else:
        # Check plugin registry, then fall back to GenericEntry
        resolved_cls = get_entry_class(entry_type)
        if resolved_cls is not GenericEntry:
            return resolved_cls.from_frontmatter(
                {
                    "id": entry_id,
                    "title": title,
                    "type": entry_type,
                    "tags": kwargs.get("tags", []),
                    "summary": kwargs.get("summary", ""),
                    **(kwargs.get("metadata") or {}),
                },
                body,
            )
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
