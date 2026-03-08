"""
pyrite Models

Core entry types for knowledge bases.
"""

from .base import Entry
from .core_types import (
    ENTRY_TYPE_REGISTRY,
    DocumentEntry,
    EventEntry,
    NoteEntry,
    OrganizationEntry,
    PersonEntry,
    RelationshipEntry,
    TimelineEntry,
    TopicEntry,
    entry_from_frontmatter,
    get_entry_class,
)
from .generic import GenericEntry
from .protocols import (
    PROTOCOL_FIELDS,
    PROTOCOL_REGISTRY,
    Assignable,
    Locatable,
    Parentable,
    Prioritizable,
    Statusable,
    Temporal,
)
from .task import TaskEntry

# Register TaskEntry in core registry (avoids circular import via core_types.py)
ENTRY_TYPE_REGISTRY["task"] = TaskEntry

__all__ = [
    "Entry",
    "NoteEntry",
    "PersonEntry",
    "OrganizationEntry",
    "EventEntry",
    "DocumentEntry",
    "TopicEntry",
    "RelationshipEntry",
    "TaskEntry",
    "TimelineEntry",
    "GenericEntry",
    "ENTRY_TYPE_REGISTRY",
    "get_entry_class",
    "entry_from_frontmatter",
    "Assignable",
    "Temporal",
    "Locatable",
    "Statusable",
    "Prioritizable",
    "Parentable",
    "PROTOCOL_REGISTRY",
    "PROTOCOL_FIELDS",
]
