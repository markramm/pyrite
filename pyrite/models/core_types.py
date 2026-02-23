"""
Core Entry Types

Pyrite ships these ~8 base types that any KB can use out of the box.
Every field is optional except title.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from ..schema import (
    EventStatus,
    Provenance,
    ResearchStatus,
    generate_entry_id,
    generate_event_id,
    validate_date,
    validate_importance,
)
from .base import Entry, parse_datetime, parse_links, parse_sources


@dataclass
class NoteEntry(Entry):
    """General-purpose knowledge note."""

    @property
    def entry_type(self) -> str:
        return "note"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "NoteEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
        )


@dataclass
class PersonEntry(Entry):
    """An individual — person profile."""

    role: str = ""
    affiliations: list[str] = field(default_factory=list)
    importance: int = 5
    research_status: ResearchStatus = ResearchStatus.STUB

    @property
    def entry_type(self) -> str:
        return "person"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.role:
            meta["role"] = self.role
        if self.affiliations:
            meta["affiliations"] = self.affiliations
        if self.importance != 5:
            meta["importance"] = self.importance
        if self.research_status != ResearchStatus.STUB:
            meta["research_status"] = self.research_status.value
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "PersonEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        status_str = meta.get("research_status", "stub")
        try:
            research_status = ResearchStatus(status_str)
        except ValueError:
            research_status = ResearchStatus.STUB

        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            role=meta.get("role", ""),
            affiliations=meta.get("affiliations", []) or [],
            importance=int(meta.get("importance", 5)),
            research_status=research_status,
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
        )

    @classmethod
    def create(cls, name: str, **kwargs) -> "PersonEntry":
        """Create a new person entry with auto-generated ID."""
        parts = name.split()
        if len(parts) >= 2:
            entry_id = f"{parts[-1].lower()}-{'-'.join(parts[:-1]).lower()}"
        else:
            entry_id = name.lower()
        entry_id = re.sub(r"[^a-z0-9-]+", "", entry_id)
        return cls(id=entry_id, title=name, **kwargs)


@dataclass
class OrganizationEntry(Entry):
    """A group, company, institution."""

    org_type: str = ""  # gov, ngo, corp, etc.
    jurisdiction: str = ""
    founded: str = ""
    importance: int = 5
    research_status: ResearchStatus = ResearchStatus.STUB

    @property
    def entry_type(self) -> str:
        return "organization"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.org_type:
            meta["org_type"] = self.org_type
        if self.jurisdiction:
            meta["jurisdiction"] = self.jurisdiction
        if self.founded:
            meta["founded"] = self.founded
        if self.importance != 5:
            meta["importance"] = self.importance
        if self.research_status != ResearchStatus.STUB:
            meta["research_status"] = self.research_status.value
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "OrganizationEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        status_str = meta.get("research_status", "stub")
        try:
            research_status = ResearchStatus(status_str)
        except ValueError:
            research_status = ResearchStatus.STUB

        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            org_type=meta.get("org_type", ""),
            jurisdiction=meta.get("jurisdiction", ""),
            founded=meta.get("founded", ""),
            importance=int(meta.get("importance", 5)),
            research_status=research_status,
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
        )

    @classmethod
    def create(cls, name: str, **kwargs) -> "OrganizationEntry":
        """Create a new organization entry with auto-generated ID."""
        entry_id = generate_entry_id(name)
        return cls(id=entry_id, title=name, **kwargs)


@dataclass
class EventEntry(Entry):
    """Something that happened — timeline event with canonical date."""

    date: str = ""  # YYYY-MM-DD
    importance: int = 5
    status: EventStatus = EventStatus.CONFIRMED
    location: str = ""
    participants: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def entry_type(self) -> str:
        return "event"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.date:
            meta["date"] = self.date
        if self.importance != 5:
            meta["importance"] = self.importance
        if self.status != EventStatus.CONFIRMED:
            meta["status"] = self.status.value
        if self.location:
            meta["location"] = self.location
        if self.participants:
            meta["participants"] = self.participants
        if self.notes:
            meta["notes"] = self.notes
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "EventEntry":
        status_str = meta.get("status", "confirmed")
        try:
            status = EventStatus(status_str)
        except ValueError:
            status = EventStatus.CONFIRMED

        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        # Support both "participants" and legacy "actors"
        participants = meta.get("participants", meta.get("actors", [])) or []

        return cls(
            id=str(meta.get("id", "")),
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            date=meta.get("date", ""),
            importance=int(meta.get("importance", 5)),
            status=status,
            location=meta.get("location", ""),
            participants=participants,
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            notes=meta.get("notes", ""),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
        )

    def validate(self) -> list[str]:
        """Validate event entry."""
        errors = super().validate()

        if not self.date:
            errors.append("Event must have a date")
        elif not validate_date(self.date):
            errors.append(f"Invalid date format: {self.date} (expected YYYY-MM-DD)")

        if not validate_importance(self.importance):
            errors.append(f"Importance must be 1-10, got: {self.importance}")

        if self.id and self.date:
            if not self.id.startswith(self.date):
                errors.append(f"Event ID should start with date: {self.date}")

        return errors

    @classmethod
    def create(cls, date: str, title: str, body: str = "", **kwargs) -> "EventEntry":
        """Create a new event with auto-generated ID."""
        event_id = generate_event_id(date, title)
        return cls(id=event_id, title=title, body=body, date=date, **kwargs)


@dataclass
class DocumentEntry(Entry):
    """A reference document."""

    date: str = ""
    author: str = ""
    document_type: str = ""
    url: str = ""
    importance: int = 5

    @property
    def entry_type(self) -> str:
        return "document"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.date:
            meta["date"] = self.date
        if self.author:
            meta["author"] = self.author
        if self.document_type:
            meta["document_type"] = self.document_type
        if self.url:
            meta["url"] = self.url
        if self.importance != 5:
            meta["importance"] = self.importance
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "DocumentEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            date=meta.get("date", ""),
            author=meta.get("author", ""),
            document_type=meta.get("document_type", ""),
            url=meta.get("url", ""),
            importance=int(meta.get("importance", 5)),
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
        )

    @classmethod
    def create(cls, title: str, **kwargs) -> "DocumentEntry":
        """Create a new document entry."""
        entry_id = generate_entry_id(title)
        return cls(id=entry_id, title=title, **kwargs)


@dataclass
class TopicEntry(Entry):
    """A theme, subject area, or concept."""

    importance: int = 5

    @property
    def entry_type(self) -> str:
        return "topic"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.importance != 5:
            meta["importance"] = self.importance
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "TopicEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            importance=int(meta.get("importance", 5)),
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
        )


@dataclass
class RelationshipEntry(Entry):
    """A connection between entities — reified relationship."""

    source_entity: str = ""
    target_entity: str = ""
    relationship_type: str = ""

    @property
    def entry_type(self) -> str:
        return "relationship"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.source_entity:
            meta["source_entity"] = self.source_entity
        if self.target_entity:
            meta["target_entity"] = self.target_entity
        if self.relationship_type:
            meta["relationship_type"] = self.relationship_type
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "RelationshipEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            source_entity=meta.get("source_entity", meta.get("source", "")),
            target_entity=meta.get("target_entity", meta.get("target", "")),
            relationship_type=meta.get("relationship_type", ""),
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
        )


@dataclass
class TimelineEntry(Entry):
    """An ordered sequence of events."""

    date_range: str = ""

    @property
    def entry_type(self) -> str:
        return "timeline"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.date_range:
            meta["date_range"] = self.date_range
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "TimelineEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            date_range=meta.get("date_range", ""),
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
        )


# Type registry: maps type name string to entry class
ENTRY_TYPE_REGISTRY: dict[str, type[Entry]] = {
    "note": NoteEntry,
    "person": PersonEntry,
    "organization": OrganizationEntry,
    "event": EventEntry,
    "document": DocumentEntry,
    "topic": TopicEntry,
    "relationship": RelationshipEntry,
    "timeline": TimelineEntry,
}


def get_entry_class(entry_type: str) -> type[Entry]:
    """Get the entry class for a type name.

    Checks core types first, then plugin registry, then falls back to GenericEntry.
    """
    if entry_type in ENTRY_TYPE_REGISTRY:
        return ENTRY_TYPE_REGISTRY[entry_type]

    # Check plugin registry for custom entry types
    try:
        from ..plugins import get_registry

        plugin_types = get_registry().get_all_entry_types()
        if entry_type in plugin_types:
            return plugin_types[entry_type]
    except Exception:
        pass

    from .generic import GenericEntry

    return GenericEntry


def entry_from_frontmatter(meta: dict[str, Any], body: str) -> Entry:
    """Create an entry from frontmatter, auto-detecting the type."""
    entry_type = meta.get("type", "note")
    cls = get_entry_class(entry_type)
    return cls.from_frontmatter(meta, body)
