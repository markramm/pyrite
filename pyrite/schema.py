"""
KB Schema Definitions

Defines core types, validation, and extensible schema system.
Supports per-KB schema customization via kb.yaml.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pyrite.utils.yaml import load_yaml_file


class VerificationStatus(StrEnum):
    """Verification status for sources and claims."""

    UNVERIFIED = "unverified"
    CLAIMED = "claimed"
    REVIEWED = "reviewed"
    VERIFIED = "verified"
    DISPUTED = "disputed"


class EventStatus(StrEnum):
    """Status for timeline events."""

    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    ALLEGED = "alleged"
    RUMORED = "rumored"


class ResearchStatus(StrEnum):
    """Research completion status."""

    STUB = "stub"
    PARTIAL = "partial"
    DRAFT = "draft"
    COMPLETE = "complete"
    PUBLISHED = "published"


# Core entry types shipped with pyrite
CORE_TYPES: dict[str, dict[str, Any]] = {
    "note": {
        "description": "General-purpose knowledge note",
        "subdirectory": "notes",
        "fields": {"tags": "list[str]", "links": "list[Link]"},
    },
    "person": {
        "description": "An individual",
        "subdirectory": "people",
        "fields": {
            "role": "str",
            "affiliations": "list[str]",
        },
    },
    "organization": {
        "description": "A group, company, institution",
        "subdirectory": "organizations",
        "fields": {
            "org_type": "str",  # gov, ngo, corp, etc.
            "jurisdiction": "str",
            "founded": "str",
        },
    },
    "event": {
        "description": "Something that happened",
        "subdirectory": "events",
        "fields": {
            "date": "str",
            "location": "str",
            "importance": "int",
            "status": "EventStatus",
            "participants": "list[str]",
        },
    },
    "document": {
        "description": "A reference document",
        "subdirectory": "documents",
        "fields": {
            "date": "str",
            "author": "str",
            "document_type": "str",
            "url": "str",
        },
    },
    "topic": {
        "description": "A theme, subject area, or concept",
        "subdirectory": "topics",
        "fields": {},
    },
    "relationship": {
        "description": "A connection between entities",
        "subdirectory": "relationships",
        "fields": {
            "source": "str",
            "target": "str",
            "relationship_type": "str",
        },
    },
    "timeline": {
        "description": "An ordered sequence of events",
        "subdirectory": "timelines",
        "fields": {
            "date_range": "str",
        },
    },
    "collection": {
        "description": "A folder-backed collection of entries",
        "subdirectory": None,  # Collections live in-place, not a dedicated folder
        "fields": {
            "source_type": "str",
            "description": "str",
            "icon": "str",
            "view_config": "dict",
            "folder_path": "str",
        },
    },
}


# =============================================================================
# Core Type Metadata — AI instructions, field descriptions, display hints
# =============================================================================

CORE_TYPE_METADATA: dict[str, dict[str, Any]] = {
    "note": {
        "ai_instructions": (
            "General-purpose knowledge note. Use for observations, analysis, "
            "summaries, or any content that doesn't fit a more specific type. "
            "Keep notes focused on a single topic."
        ),
        "field_descriptions": {
            "title": "Descriptive title summarizing the note's content",
            "tags": "Categorization tags for discovery and filtering",
            "links": "Typed relationships to other entries",
            "summary": "Brief one-line summary of the note",
        },
        "display": {"icon": "file-text", "layout": "document"},
    },
    "event": {
        "ai_instructions": (
            "A specific occurrence with a known or approximate date. Always "
            "include a date. Set importance 1-10 based on significance. Use "
            "participants to link people/orgs involved."
        ),
        "field_descriptions": {
            "date": "When the event occurred (YYYY-MM-DD)",
            "importance": "Significance score from 1 (minor) to 10 (major)",
            "status": "Verification status: confirmed, disputed, alleged, rumored",
            "location": "Where the event took place",
            "participants": "People or organizations involved",
        },
        "display": {"icon": "calendar", "layout": "record"},
    },
    "person": {
        "ai_instructions": (
            "An individual person. Use role to describe their primary function "
            "or position. List organizational affiliations. Set importance "
            "based on relevance to research."
        ),
        "field_descriptions": {
            "role": "Primary role, title, or position",
            "affiliations": "Organizations this person is associated with",
            "importance": "Relevance score from 1 (peripheral) to 10 (central)",
            "research_status": "How complete the profile is: stub, partial, draft, complete, published",
        },
        "display": {"icon": "user", "layout": "record"},
    },
    "organization": {
        "ai_instructions": (
            "A group, company, government body, or institution. Specify "
            "org_type (gov, ngo, corp, media, political, military, etc.) "
            "and jurisdiction where relevant."
        ),
        "field_descriptions": {
            "org_type": "Category: gov, ngo, corp, media, political, military, academic, religious, etc.",
            "jurisdiction": "Geographic or legal jurisdiction",
            "founded": "Date or year the organization was established",
            "importance": "Relevance score from 1 to 10",
        },
        "display": {"icon": "building", "layout": "record"},
    },
    "document": {
        "ai_instructions": (
            "A reference to an external document: report, filing, memo, "
            "article, etc. Always include the source URL when available. "
            "Use document_type to classify."
        ),
        "field_descriptions": {
            "date": "Publication or filing date",
            "author": "Author or issuing body",
            "document_type": "Category: report, filing, memo, article, press-release, court-document, etc.",
            "url": "URL to the original document",
        },
        "display": {"icon": "file", "layout": "document"},
    },
    "topic": {
        "ai_instructions": (
            "A theme, subject area, or concept that entries can be organized "
            "around. Use as a hub to connect related entries via links and tags."
        ),
        "field_descriptions": {
            "importance": "Centrality of this topic to the research, 1-10",
        },
        "display": {"icon": "hash", "layout": "document"},
    },
    "relationship": {
        "ai_instructions": (
            "A reified relationship between two entities. Use when the "
            "relationship itself has properties worth tracking (dates, "
            "evidence, context). For simple links, use the links field instead."
        ),
        "field_descriptions": {
            "source_entity": "Entry ID of the source entity",
            "target_entity": "Entry ID of the target entity",
            "relationship_type": "Type of relationship (see relationship_types in schema)",
        },
        "display": {"icon": "link", "layout": "record"},
    },
    "timeline": {
        "ai_instructions": (
            "An ordered sequence of related events. Use to group events "
            "into a narrative arc. Reference individual events via links."
        ),
        "field_descriptions": {
            "date_range": "Time span covered, e.g. '2024-01 to 2025-06'",
        },
        "display": {"icon": "clock", "layout": "document"},
    },
    "collection": {
        "ai_instructions": (
            "A folder-backed collection that groups related entries. "
            "Created automatically from __collection.yaml files in KB folders. "
            "Use to organize entries into browsable groups with list or table views."
        ),
        "field_descriptions": {
            "source_type": "Collection source: 'folder' for filesystem-backed",
            "description": "Human-readable description of the collection's purpose",
            "icon": "Icon identifier for display",
            "view_config": "View settings: default_view, table_columns",
            "folder_path": "Relative path to the folder within the KB",
        },
        "display": {"icon": "folder", "layout": "record"},
    },
}


@dataclass
class Source:
    """
    Source reference with verification metadata.

    This is a first-class object for tracking provenance.
    """

    title: str
    url: str
    outlet: str = ""
    date: str | None = None
    author: str = ""
    source_type: str = "news"
    verified: bool = False
    verified_date: str | None = None
    verified_by: str = ""
    archive_url: str = ""
    key_facts_confirmed: list[str] = field(default_factory=list)
    confidence: str = "unverified"  # high, medium, low, unverified
    access: str = "public"  # public, paywalled, restricted, offline

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {"title": self.title, "url": self.url}
        if self.outlet:
            result["outlet"] = self.outlet
        if self.date:
            result["date"] = self.date
        if self.author:
            result["author"] = self.author
        if self.source_type != "news":
            result["type"] = self.source_type
        if self.verified:
            result["verified"] = self.verified
            if self.verified_date:
                result["verified_date"] = self.verified_date
            if self.verified_by:
                result["verified_by"] = self.verified_by
        if self.archive_url:
            result["archive_url"] = self.archive_url
        if self.key_facts_confirmed:
            result["key_facts_confirmed"] = self.key_facts_confirmed
        if self.confidence != "unverified":
            result["confidence"] = self.confidence
        if self.access != "public":
            result["access"] = self.access
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Source":
        """Create from dictionary."""
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            outlet=data.get("outlet", ""),
            date=data.get("date"),
            author=data.get("author", ""),
            source_type=data.get("type", "news"),
            verified=data.get("verified", False),
            verified_date=data.get("verified_date"),
            verified_by=data.get("verified_by", ""),
            archive_url=data.get("archive_url", ""),
            key_facts_confirmed=data.get("key_facts_confirmed", []),
            confidence=data.get("confidence", "unverified"),
            access=data.get("access", "public"),
        )


@dataclass
class Link:
    """
    Typed relationship between entries.

    Supports both Zettelkasten-style note links and entity relationships.
    """

    target: str  # Target entry ID or path
    relation: str  # Relationship type
    note: str = ""  # Optional description
    kb: str = ""  # Target KB (if cross-KB link)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {"target": self.target, "relation": self.relation}
        if self.note:
            result["note"] = self.note
        if self.kb:
            result["kb"] = self.kb
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Link":
        """Create from dictionary."""
        # Handle legacy format {to: id, type: relation}
        if "to" in data:
            return cls(
                target=data["to"],
                relation=data.get("type", "related"),
                note=data.get("description", ""),
            )
        return cls(
            target=data.get("target", ""),
            relation=data.get("relation", "related"),
            note=data.get("note", ""),
            kb=data.get("kb", ""),
        )


# Relationship types with inverses
RELATIONSHIP_TYPES: dict[str, dict[str, Any]] = {
    # Entity relationships
    "owns": {"inverse": "owned_by", "description": "Ownership relationship"},
    "owned_by": {"inverse": "owns", "description": "Owned by another entity"},
    "controls": {"inverse": "controlled_by", "description": "Control relationship"},
    "controlled_by": {"inverse": "controls", "description": "Controlled by another entity"},
    "directs": {"inverse": "directed_by", "description": "Directorship"},
    "directed_by": {"inverse": "directs", "description": "Directed by another entity"},
    "advises": {"inverse": "advised_by", "description": "Advisory relationship"},
    "advised_by": {"inverse": "advises", "description": "Advised by another entity"},
    "member_of": {"inverse": "has_member", "description": "Membership"},
    "has_member": {"inverse": "member_of", "description": "Has member"},
    "employed_by": {"inverse": "employs", "description": "Employment relationship"},
    "employs": {"inverse": "employed_by", "description": "Employs"},
    "funds": {"inverse": "funded_by", "description": "Funding relationship"},
    "funded_by": {"inverse": "funds", "description": "Funded by"},
    "authored": {"inverse": "authored_by", "description": "Authorship"},
    "authored_by": {"inverse": "authored", "description": "Authored by"},
    "mentions": {"inverse": "mentioned_by", "description": "Mentions"},
    "mentioned_by": {"inverse": "mentions", "description": "Mentioned by"},
    "involves": {"inverse": "involved_in", "description": "Involvement"},
    "involved_in": {"inverse": "involves", "description": "Involved in"},
    "located_at": {"inverse": "location_of", "description": "Location relationship"},
    "location_of": {"inverse": "located_at", "description": "Location of"},
    "related_to": {"inverse": "related_to", "description": "General relationship"},
    # Zettelkasten note relationships
    "supports": {"inverse": "supported_by", "description": "Evidence supporting a claim"},
    "supported_by": {"inverse": "supports", "description": "Supported by evidence"},
    "contradicts": {"inverse": "contradicted_by", "description": "Contradicting evidence"},
    "contradicted_by": {"inverse": "contradicts", "description": "Contradicted by"},
    "extends": {"inverse": "extended_by", "description": "Extends or elaborates on"},
    "extended_by": {"inverse": "extends", "description": "Extended by"},
    "refines": {"inverse": "refined_by", "description": "Refines or narrows"},
    "refined_by": {"inverse": "refines", "description": "Refined by"},
    "is_example_of": {"inverse": "has_example", "description": "Example of a concept"},
    "has_example": {"inverse": "is_example_of", "description": "Has example"},
    "causally_precedes": {"inverse": "causally_follows", "description": "Causal predecessor"},
    "causally_follows": {"inverse": "causally_precedes", "description": "Causal successor"},
    "asks_question": {"inverse": "answers_question", "description": "Poses a question"},
    "answers_question": {"inverse": "asks_question", "description": "Answers a question"},
    "is_part_of": {"inverse": "contains_part", "description": "Part of a larger whole"},
    "contains_part": {"inverse": "is_part_of", "description": "Contains a part"},
    # Body wikilink references
    "wikilink": {"inverse": "wikilinked_by", "description": "Inline wikilink reference"},
    "wikilinked_by": {"inverse": "wikilink", "description": "Referenced by inline wikilink"},
}


def get_all_relationship_types() -> dict[str, dict[str, Any]]:
    """Get all relationship types: core + plugin-provided."""
    all_types = dict(RELATIONSHIP_TYPES)
    try:
        from .plugins import get_registry

        all_types.update(get_registry().get_all_relationship_types())
    except Exception:
        pass
    return all_types


def get_inverse_relation(relation: str) -> str:
    """Get the inverse of a relationship type."""
    all_types = get_all_relationship_types()
    if relation in all_types:
        return all_types[relation]["inverse"]
    return "related_to"


def resolve_type_metadata(type_name: str, kb_schema: "KBSchema | None" = None) -> dict[str, Any]:
    """Resolve type metadata using 4-layer precedence.

    Resolution order (highest priority first):
        1. KB-level overrides from kb.yaml
        2. Plugin metadata via get_type_metadata()
        3. Core defaults from CORE_TYPE_METADATA
        4. Empty defaults

    Returns:
        Dict with keys: ai_instructions, field_descriptions, display.
    """
    result: dict[str, Any] = {"ai_instructions": "", "field_descriptions": {}, "display": {}}

    # Layer 1: Core defaults (lowest priority base)
    if type_name in CORE_TYPE_METADATA:
        core = CORE_TYPE_METADATA[type_name]
        result["ai_instructions"] = core.get("ai_instructions", "")
        result["field_descriptions"] = dict(core.get("field_descriptions", {}))
        result["display"] = dict(core.get("display", {}))

    # Layer 2: Plugin metadata (overrides core)
    try:
        from .plugins import get_registry

        plugin_meta = get_registry().get_all_type_metadata()
        if type_name in plugin_meta:
            pm = plugin_meta[type_name]
            if pm.get("ai_instructions"):
                result["ai_instructions"] = pm["ai_instructions"]
            result["field_descriptions"].update(pm.get("field_descriptions", {}))
            result["display"].update(pm.get("display", {}))
    except Exception:
        pass

    # Layer 3: KB-level overrides (highest priority)
    if kb_schema and type_name in kb_schema.types:
        ts = kb_schema.types[type_name]
        if ts.ai_instructions:
            result["ai_instructions"] = ts.ai_instructions
        if ts.field_descriptions:
            result["field_descriptions"].update(ts.field_descriptions)
        if ts.display:
            result["display"].update(ts.display)

    return result


@dataclass
class Provenance:
    """
    Provenance tracking for distributed research.

    Tracks who contributed what and when.
    """

    created_by: str = ""
    created_date: str = ""
    last_modified_by: str = ""
    last_modified_date: str = ""
    contributors: list[str] = field(default_factory=list)
    agent_version: str = ""  # For AI agent contributions
    agent_confidence: float = 1.0
    requires_human_review: bool = False
    auto_generated_fields: list[str] = field(default_factory=list)
    human_verified_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (only non-empty fields)."""
        result = {}
        if self.created_by:
            result["created_by"] = self.created_by
        if self.created_date:
            result["created_date"] = self.created_date
        if self.last_modified_by:
            result["last_modified_by"] = self.last_modified_by
        if self.last_modified_date:
            result["last_modified_date"] = self.last_modified_date
        if self.contributors:
            result["contributors"] = self.contributors
        if self.agent_version:
            result["agent_version"] = self.agent_version
            result["agent_confidence"] = self.agent_confidence
        if self.requires_human_review:
            result["requires_human_review"] = self.requires_human_review
        if self.auto_generated_fields:
            result["auto_generated_fields"] = self.auto_generated_fields
        if self.human_verified_fields:
            result["human_verified_fields"] = self.human_verified_fields
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Provenance":
        """Create from dictionary."""
        return cls(
            created_by=data.get("created_by", ""),
            created_date=data.get("created_date", ""),
            last_modified_by=data.get("last_modified_by", ""),
            last_modified_date=data.get("last_modified_date", ""),
            contributors=data.get("contributors", []),
            agent_version=data.get("agent_version", ""),
            agent_confidence=data.get("agent_confidence", 1.0),
            requires_human_review=data.get("requires_human_review", False),
            auto_generated_fields=data.get("auto_generated_fields", []),
            human_verified_fields=data.get("human_verified_fields", []),
        )


# Validation utilities


def validate_date(date_str: str) -> bool:
    """Validate date string format (YYYY-MM-DD)."""
    if not date_str:
        return False
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(pattern, date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_importance(importance: Any) -> bool:
    """Validate importance is 1-10."""
    try:
        val = int(importance)
        return 1 <= val <= 10
    except (ValueError, TypeError):
        return False


def validate_event_id(event_id: str) -> bool:
    """Validate event ID format (YYYY-MM-DD--slug)."""
    pattern = r"^\d{4}-\d{2}-\d{2}--[a-z0-9-]+$"
    return bool(re.match(pattern, event_id))


def generate_event_id(date: str, title: str) -> str:
    """Generate event ID from date and title."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50]
    return f"{date}--{slug}"


def generate_entry_id(title: str) -> str:
    """Generate entry ID from title."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


# =============================================================================
# Extensible Schema System
# =============================================================================


@dataclass
class FieldSchema:
    """Schema definition for a single typed field.

    Supports 10 field types: text, number, date, datetime, checkbox,
    select, multi-select, object-ref, list, tags.
    """

    name: str
    field_type: str = "text"
    required: bool = False
    default: Any = None
    description: str = ""
    options: list[str] = field(default_factory=list)  # for select/multi-select
    items: dict[str, Any] = field(default_factory=dict)  # for list type
    constraints: dict[str, Any] = field(default_factory=dict)  # min, max, format, target_type

    VALID_TYPES = frozenset(
        [
            "text",
            "number",
            "date",
            "datetime",
            "checkbox",
            "select",
            "multi-select",
            "object-ref",
            "list",
            "tags",
        ]
    )

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "FieldSchema":
        """Parse a field definition from kb.yaml."""
        constraints = {}
        for key in ("format", "min_length", "max_length", "min", "max", "target_type"):
            if key in data:
                constraints[key] = data[key]

        return cls(
            name=name,
            field_type=data.get("type", "text"),
            required=data.get("required", False),
            default=data.get("default"),
            description=data.get("description", ""),
            options=data.get("options", []),
            items=data.get("items", {}),
            constraints=constraints,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for agent schema and API responses."""
        result: dict[str, Any] = {"type": self.field_type}
        if self.required:
            result["required"] = True
        if self.default is not None:
            result["default"] = self.default
        if self.description:
            result["description"] = self.description
        if self.options:
            result["options"] = self.options
        if self.items:
            result["items"] = self.items
        result.update(self.constraints)
        return result


@dataclass
class TypeSchema:
    """Schema definition for an entry type (core or custom)."""

    name: str
    description: str = ""
    required: list[str] = field(default_factory=lambda: ["title"])
    optional: list[str] = field(default_factory=list)
    subdirectory: str = ""
    fields: dict[str, FieldSchema] = field(default_factory=dict)
    layout: str = ""  # "document" or "record"
    ai_instructions: str = ""
    field_descriptions: dict[str, str] = field(default_factory=dict)
    display: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"description": self.description}
        if self.required != ["title"]:
            result["required"] = self.required
        if self.optional:
            result["optional"] = self.optional
        if self.subdirectory:
            result["subdirectory"] = self.subdirectory
        if self.fields:
            result["fields"] = {name: fs.to_dict() for name, fs in self.fields.items()}
        if self.layout:
            result["layout"] = self.layout
        if self.ai_instructions:
            result["ai_instructions"] = self.ai_instructions
        if self.field_descriptions:
            result["field_descriptions"] = self.field_descriptions
        if self.display:
            result["display"] = self.display
        return result


def _validate_field_value(
    field_name: str, value: Any, field_schema: FieldSchema
) -> list[dict[str, Any]]:
    """Validate a field value against its FieldSchema. Returns list of error dicts."""
    errors: list[dict[str, Any]] = []
    ft = field_schema.field_type

    if ft == "number":
        try:
            num = int(value) if isinstance(value, int) else float(value)
            min_val = field_schema.constraints.get("min")
            max_val = field_schema.constraints.get("max")
            if min_val is not None and num < min_val:
                errors.append(
                    {
                        "field": field_name,
                        "rule": "field_range",
                        "expected": f">= {min_val}",
                        "got": value,
                    }
                )
            if max_val is not None and num > max_val:
                errors.append(
                    {
                        "field": field_name,
                        "rule": "field_range",
                        "expected": f"<= {max_val}",
                        "got": value,
                    }
                )
        except (ValueError, TypeError):
            errors.append(
                {
                    "field": field_name,
                    "rule": "field_number",
                    "expected": "numeric value",
                    "got": value,
                }
            )

    elif ft == "date":
        if isinstance(value, str) and not validate_date(value):
            errors.append(
                {
                    "field": field_name,
                    "rule": "field_date",
                    "expected": "YYYY-MM-DD",
                    "got": value,
                }
            )

    elif ft == "datetime":
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value)
            except ValueError:
                errors.append(
                    {
                        "field": field_name,
                        "rule": "field_datetime",
                        "expected": "ISO 8601 datetime",
                        "got": value,
                    }
                )

    elif ft == "checkbox":
        if not isinstance(value, bool):
            errors.append(
                {
                    "field": field_name,
                    "rule": "field_checkbox",
                    "expected": "boolean",
                    "got": type(value).__name__,
                }
            )

    elif ft == "select":
        if field_schema.options and value not in field_schema.options:
            errors.append(
                {
                    "field": field_name,
                    "rule": "field_select",
                    "expected": field_schema.options,
                    "got": value,
                }
            )

    elif ft == "multi-select":
        if isinstance(value, list) and field_schema.options:
            invalid = [v for v in value if v not in field_schema.options]
            if invalid:
                errors.append(
                    {
                        "field": field_name,
                        "rule": "field_multi_select",
                        "expected": field_schema.options,
                        "got": invalid,
                    }
                )
        elif not isinstance(value, list):
            errors.append(
                {
                    "field": field_name,
                    "rule": "field_multi_select",
                    "expected": "list",
                    "got": type(value).__name__,
                }
            )

    # text, object-ref, list, tags — no validation beyond presence (for now)

    return errors


@dataclass
class KBSchema:
    """Schema for a knowledge base, loaded from kb.yaml."""

    name: str = ""
    description: str = ""
    types: dict[str, TypeSchema] = field(default_factory=dict)
    policies: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> "KBSchema":
        """Load schema from kb.yaml file."""
        if not path.exists():
            return cls()

        data = load_yaml_file(path)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KBSchema":
        """Create from dictionary."""
        types = {}
        for type_name, type_data in data.get("types", {}).items():
            if isinstance(type_data, dict):
                # Parse rich field definitions if present
                fields = {}
                for field_name, field_data in type_data.get("fields", {}).items():
                    if isinstance(field_data, dict):
                        fields[field_name] = FieldSchema.from_dict(field_name, field_data)

                types[type_name] = TypeSchema(
                    name=type_name,
                    description=type_data.get("description", ""),
                    required=type_data.get("required", ["title"]),
                    optional=type_data.get("optional", []),
                    subdirectory=type_data.get("subdirectory", ""),
                    fields=fields,
                    layout=type_data.get("layout", ""),
                    ai_instructions=type_data.get("ai_instructions", ""),
                    field_descriptions=type_data.get("field_descriptions", {}),
                    display=type_data.get("display", {}),
                )
            else:
                types[type_name] = TypeSchema(name=type_name)

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            types=types,
            policies=data.get("policies", {}),
            validation=data.get("validation", {}),
        )

    def get_type_schema(self, entry_type: str) -> TypeSchema | None:
        """Get schema for a type, checking KB customizations then core types."""
        if entry_type in self.types:
            return self.types[entry_type]
        if entry_type in CORE_TYPES:
            core = CORE_TYPES[entry_type]
            return TypeSchema(
                name=entry_type,
                description=core["description"],
                subdirectory=core["subdirectory"],
            )
        return None

    def get_subdirectory(self, entry_type: str) -> str:
        """Get the subdirectory for an entry type."""
        type_schema = self.get_type_schema(entry_type)
        if type_schema and type_schema.subdirectory:
            return type_schema.subdirectory
        if entry_type in CORE_TYPES:
            return CORE_TYPES[entry_type]["subdirectory"]
        return f"{entry_type}s"  # Default: plural of type name

    def to_agent_schema(self) -> dict[str, Any]:
        """Export schema in agent-friendly format for kb_schema MCP tool."""
        types_dict = {}

        # Include core types
        for type_name, core_def in CORE_TYPES.items():
            type_info: dict[str, Any] = {
                "description": core_def["description"],
                "fields": core_def["fields"],
            }
            # Apply KB customizations
            if type_name in self.types:
                kb_type = self.types[type_name]
                if kb_type.required != ["title"]:
                    type_info["required"] = kb_type.required
                if kb_type.optional:
                    type_info["optional"] = kb_type.optional

            # Include resolved type metadata
            metadata = resolve_type_metadata(type_name, self)
            if metadata["ai_instructions"]:
                type_info["ai_instructions"] = metadata["ai_instructions"]
            if metadata["field_descriptions"]:
                type_info["field_descriptions"] = metadata["field_descriptions"]
            if metadata["display"]:
                type_info["display"] = metadata["display"]

            types_dict[type_name] = type_info

        # Include custom types
        for type_name, type_schema in self.types.items():
            if type_name not in CORE_TYPES:
                type_dict = type_schema.to_dict()
                # Also resolve metadata for custom types (plugin metadata may exist)
                metadata = resolve_type_metadata(type_name, self)
                if metadata["ai_instructions"]:
                    type_dict["ai_instructions"] = metadata["ai_instructions"]
                if metadata["field_descriptions"]:
                    type_dict["field_descriptions"] = metadata["field_descriptions"]
                if metadata["display"]:
                    type_dict["display"] = metadata["display"]
                types_dict[type_name] = type_dict

        result: dict[str, Any] = {"types": types_dict}

        if self.policies:
            result["policies"] = self.policies

        # Include relationship types (core + plugin)
        all_rels = get_all_relationship_types()
        result["relationship_types"] = {
            name: info["description"]
            for name, info in all_rels.items()
            if info["inverse"] != name  # Skip self-inverse duplicates
        }

        return result

    def validate_entry(
        self,
        entry_type: str,
        fields: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate an entry against the schema. Returns structured validation result."""
        errors = []
        warnings = []

        type_schema = self.get_type_schema(entry_type)
        if not type_schema:
            # Unknown type is OK if validation isn't enforced
            if self.validation.get("enforce", False):
                errors.append(
                    {
                        "field": "entry_type",
                        "rule": "known_type",
                        "expected": list(CORE_TYPES.keys()) + list(self.types.keys()),
                        "got": entry_type,
                    }
                )
            # Don't return early — still run plugin validators below
        else:
            # Check required fields (from required list)
            for req_field in type_schema.required:
                if req_field not in fields or not fields[req_field]:
                    errors.append(
                        {
                            "field": req_field,
                            "rule": "required",
                            "expected": "non-empty value",
                            "got": fields.get(req_field),
                        }
                    )

            # Validate typed fields from FieldSchema definitions
            enforce = self.validation.get("enforce", False)
            for field_name, field_schema in type_schema.fields.items():
                # Check required fields from field schema
                if field_schema.required and (field_name not in fields or not fields[field_name]):
                    errors.append(
                        {
                            "field": field_name,
                            "rule": "required",
                            "expected": "non-empty value",
                            "got": fields.get(field_name),
                        }
                    )
                    continue

                # Skip validation if field not present (optional)
                if field_name not in fields:
                    continue

                value = fields[field_name]
                field_errors = _validate_field_value(field_name, value, field_schema)
                for item in field_errors:
                    if enforce:
                        errors.append(item)
                    else:
                        item["severity"] = "warning"
                        warnings.append(item)

        # Check validation rules
        for rule in self.validation.get("rules", []):
            field_name = rule.get("field")
            if field_name not in fields:
                continue

            value = fields[field_name]

            if "range" in rule:
                low, high = rule["range"]
                try:
                    if not (low <= int(value) <= high):
                        item = {
                            "field": field_name,
                            "rule": "range",
                            "expected": rule["range"],
                            "got": value,
                        }
                        if self.validation.get("enforce", False):
                            errors.append(item)
                        else:
                            item["severity"] = "warning"
                            warnings.append(item)
                except (ValueError, TypeError):
                    pass

            if "format" in rule and rule["format"] == "ISO8601":
                if isinstance(value, str) and not validate_date(value):
                    item = {
                        "field": field_name,
                        "rule": "format",
                        "expected": "ISO8601 (YYYY-MM-DD)",
                        "got": value,
                    }
                    if self.validation.get("enforce", False):
                        errors.append(item)
                    else:
                        item["severity"] = "warning"
                        warnings.append(item)

        # Check policies
        min_sources = self.policies.get("minimum_sources", 0)
        if min_sources > 0:
            sources = fields.get("sources", [])
            if len(sources) < min_sources:
                item = {
                    "field": "sources",
                    "rule": "minimum_sources",
                    "expected": min_sources,
                    "got": len(sources),
                    "severity": "warning",
                }
                warnings.append(item)

        # Run plugin validators
        try:
            from .plugins import get_registry

            ctx = context or {}
            for validator in get_registry().get_all_validators():
                try:
                    results = validator(entry_type, fields, ctx)
                    for item in results or []:
                        if item.get("severity") == "warning":
                            warnings.append(item)
                        else:
                            errors.append(item)
                except TypeError:
                    # Fallback for validators with old (entry_type, data) signature
                    try:
                        results = validator(entry_type, fields)
                        for item in results or []:
                            if item.get("severity") == "warning":
                                warnings.append(item)
                            else:
                                errors.append(item)
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
