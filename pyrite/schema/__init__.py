"""
KB Schema Definitions

Defines core types, validation, and extensible schema system.
Supports per-KB schema customization via kb.yaml.
"""

from .core_types import CORE_TYPE_METADATA, CORE_TYPES, resolve_type_metadata
from .enums import EventStatus, ResearchStatus, VerificationStatus
from .field_schema import (
    FieldSchema,
    TypeSchema,
    _validate_field_value,
    expand_subdirectory_template,
)
from .kb_schema import KBSchema
from .provenance import (
    RELATIONSHIP_TYPES,
    Link,
    Provenance,
    Source,
    get_all_relationship_types,
    get_inverse_relation,
)
from .validators import (
    generate_entry_id,
    generate_event_id,
    validate_date,
    validate_event_id,
    validate_importance,
)

__all__ = [
    "CORE_TYPE_METADATA",
    "CORE_TYPES",
    "EventStatus",
    "FieldSchema",
    "KBSchema",
    "Link",
    "Provenance",
    "RELATIONSHIP_TYPES",
    "ResearchStatus",
    "Source",
    "TypeSchema",
    "VerificationStatus",
    "_validate_field_value",
    "expand_subdirectory_template",
    "generate_entry_id",
    "generate_event_id",
    "get_all_relationship_types",
    "get_inverse_relation",
    "resolve_type_metadata",
    "validate_date",
    "validate_event_id",
    "validate_importance",
]
