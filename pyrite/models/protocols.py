"""
Entry Protocol Mixins

Composable field protocols for entry types. Each protocol defines a set of
related fields that entry types can opt into via multiple inheritance.

See ADR-0017 for design rationale.
"""

import dataclasses
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class Assignable:
    """Protocol for entries that can be assigned to someone."""

    PROTOCOL_VERSION: ClassVar[int] = 1

    assignee: str = ""
    assigned_at: str = ""  # ISO 8601 datetime

    def _assignable_to_frontmatter(self) -> dict[str, Any]:
        """Return non-default Assignable fields for frontmatter."""
        result: dict[str, Any] = {}
        if self.assignee:
            result["assignee"] = self.assignee
        if self.assigned_at:
            result["assigned_at"] = self.assigned_at
        return result

    @staticmethod
    def _assignable_from_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
        """Extract Assignable fields from frontmatter dict."""
        return {
            "assignee": meta.get("assignee", ""),
            "assigned_at": meta.get("assigned_at", ""),
        }


@dataclass
class Temporal:
    """Protocol for entries with date/time information."""

    PROTOCOL_VERSION: ClassVar[int] = 1

    date: str = ""  # YYYY-MM-DD
    start_date: str = ""  # YYYY-MM-DD
    end_date: str = ""  # YYYY-MM-DD
    due_date: str = ""  # YYYY-MM-DD

    def _temporal_to_frontmatter(self) -> dict[str, Any]:
        """Return non-default Temporal fields for frontmatter."""
        result: dict[str, Any] = {}
        if self.date:
            result["date"] = self.date
        if self.start_date:
            result["start_date"] = self.start_date
        if self.end_date:
            result["end_date"] = self.end_date
        if self.due_date:
            result["due_date"] = self.due_date
        return result

    @staticmethod
    def _temporal_from_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
        """Extract Temporal fields from frontmatter dict."""
        return {
            "date": meta.get("date", ""),
            "start_date": meta.get("start_date", ""),
            "end_date": meta.get("end_date", ""),
            "due_date": meta.get("due_date", ""),
        }


@dataclass
class Locatable:
    """Protocol for entries with location information."""

    PROTOCOL_VERSION: ClassVar[int] = 1

    location: str = ""
    coordinates: str = ""  # "lat,lon"

    def _locatable_to_frontmatter(self) -> dict[str, Any]:
        """Return non-default Locatable fields for frontmatter."""
        result: dict[str, Any] = {}
        if self.location:
            result["location"] = self.location
        if self.coordinates:
            result["coordinates"] = self.coordinates
        return result

    @staticmethod
    def _locatable_from_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
        """Extract Locatable fields from frontmatter dict."""
        return {
            "location": meta.get("location", ""),
            "coordinates": meta.get("coordinates", ""),
        }


@dataclass
class Statusable:
    """Protocol for entries with workflow status."""

    PROTOCOL_VERSION: ClassVar[int] = 1

    status: str = ""

    def _statusable_to_frontmatter(self) -> dict[str, Any]:
        """Return non-default Statusable fields for frontmatter."""
        result: dict[str, Any] = {}
        if self.status:
            result["status"] = self.status
        return result

    @staticmethod
    def _statusable_from_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
        """Extract Statusable fields from frontmatter dict."""
        return {
            "status": meta.get("status", ""),
        }


@dataclass
class Prioritizable:
    """Protocol for entries with priority ranking."""

    PROTOCOL_VERSION: ClassVar[int] = 1

    priority: int = 0

    def _prioritizable_to_frontmatter(self) -> dict[str, Any]:
        """Return non-default Prioritizable fields for frontmatter."""
        result: dict[str, Any] = {}
        if self.priority:
            result["priority"] = self.priority
        return result

    @staticmethod
    def _prioritizable_from_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
        """Extract Prioritizable fields from frontmatter dict."""
        from ..utils.parse import safe_int

        return {
            "priority": safe_int(meta.get("priority"), 0),
        }


@dataclass
class Parentable:
    """Protocol for entries with parent-child hierarchy."""

    PROTOCOL_VERSION: ClassVar[int] = 1

    parent: str = ""

    def _parentable_to_frontmatter(self) -> dict[str, Any]:
        """Return non-default Parentable fields for frontmatter."""
        result: dict[str, Any] = {}
        if self.parent:
            result["parent"] = self.parent
        return result

    @staticmethod
    def _parentable_from_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
        """Extract Parentable fields from frontmatter dict."""
        return {
            "parent": meta.get("parent", ""),
        }


# Registry of protocol name -> mixin class
PROTOCOL_REGISTRY: dict[str, type] = {
    "assignable": Assignable,
    "temporal": Temporal,
    "locatable": Locatable,
    "statusable": Statusable,
    "prioritizable": Prioritizable,
    "parentable": Parentable,
}

# Map protocol field names to their protocol class
PROTOCOL_FIELDS: dict[str, type] = {
    "assignee": Assignable,
    "assigned_at": Assignable,
    "date": Temporal,
    "start_date": Temporal,
    "end_date": Temporal,
    "due_date": Temporal,
    "location": Locatable,
    "coordinates": Locatable,
    "status": Statusable,
    "priority": Prioritizable,
    "parent": Parentable,
}

# Field names promoted to DB columns by IndexManager
PROTOCOL_COLUMN_KEYS: frozenset[str] = frozenset(PROTOCOL_FIELDS.keys())


# =========================================================================
# Protocol info and satisfaction checking
# =========================================================================


def get_protocol_info(protocol_name: str) -> dict[str, Any] | None:
    """Get protocol info: version, fields, and mixin class."""
    cls = PROTOCOL_REGISTRY.get(protocol_name)
    if cls is None:
        return None
    return {
        "name": protocol_name,
        "version": getattr(cls, "PROTOCOL_VERSION", 0),
        "fields": [f.name for f in dataclasses.fields(cls)],
        "mixin_class": cls,
    }


def get_all_protocol_info() -> dict[str, dict[str, Any]]:
    """Get info for all registered protocols."""
    result = {}
    for name in PROTOCOL_REGISTRY:
        info = get_protocol_info(name)
        if info:
            result[name] = info
    return result


@dataclass
class ProtocolCheckResult:
    """Result of checking one protocol against one type."""

    protocol_name: str
    type_name: str
    satisfied: bool
    method: str  # "nominal" | "structural" | "schema" | "unknown"
    missing_fields: list[str] = field(default_factory=list)
    message: str = ""


def check_protocol_satisfaction(
    entry_class: type,
    protocol_names: list[str],
    type_schema: Any | None = None,
) -> list[ProtocolCheckResult]:
    """Check whether an entry class satisfies declared protocols.

    Uses three-tier checking:
    1. Nominal: class inherits the protocol mixin
    2. Structural: class has the protocol's fields as dataclass fields
    3. Schema: TypeSchema declares fields matching the protocol (for GenericEntry)

    Args:
        entry_class: The entry class to check.
        protocol_names: List of protocol names the type declares.
        type_schema: Optional TypeSchema for schema-level checking.

    Returns:
        List of ProtocolCheckResult, one per protocol.
    """
    results = []
    for proto_name in protocol_names:
        proto_cls = PROTOCOL_REGISTRY.get(proto_name)
        if proto_cls is None:
            # Check plugin-provided protocols
            try:
                from pyrite.plugins import get_registry

                all_protos = get_registry().get_all_protocols()
                proto_cls = all_protos.get(proto_name)
            except Exception:
                pass

        if proto_cls is None:
            results.append(
                ProtocolCheckResult(
                    protocol_name=proto_name,
                    type_name=entry_class.__name__,
                    satisfied=False,
                    method="unknown",
                    message=f"Unknown protocol '{proto_name}'",
                )
            )
            continue

        proto_fields = {f.name for f in dataclasses.fields(proto_cls)}

        # Tier 1: Nominal check (class inherits the mixin)
        try:
            if issubclass(entry_class, proto_cls):
                results.append(
                    ProtocolCheckResult(
                        protocol_name=proto_name,
                        type_name=entry_class.__name__,
                        satisfied=True,
                        method="nominal",
                    )
                )
                continue
        except TypeError:
            pass

        # Tier 2: Structural check (dataclass fields match)
        try:
            class_fields = {f.name for f in dataclasses.fields(entry_class)}
            missing = proto_fields - class_fields
            if not missing:
                results.append(
                    ProtocolCheckResult(
                        protocol_name=proto_name,
                        type_name=entry_class.__name__,
                        satisfied=True,
                        method="structural",
                    )
                )
                continue
        except TypeError:
            missing = proto_fields

        # Tier 3: Schema check (for GenericEntry-backed types)
        if type_schema is not None:
            schema_fields: set[str] = set()
            if hasattr(type_schema, "fields"):
                schema_fields |= set(type_schema.fields.keys())
            if hasattr(type_schema, "required"):
                schema_fields |= set(type_schema.required)
            if hasattr(type_schema, "optional"):
                schema_fields |= set(type_schema.optional)
            missing_from_schema = proto_fields - schema_fields
            if not missing_from_schema:
                results.append(
                    ProtocolCheckResult(
                        protocol_name=proto_name,
                        type_name=entry_class.__name__,
                        satisfied=True,
                        method="schema",
                    )
                )
                continue
            missing = missing_from_schema

        results.append(
            ProtocolCheckResult(
                protocol_name=proto_name,
                type_name=entry_class.__name__,
                satisfied=False,
                method="structural",
                missing_fields=sorted(missing),
                message=f"Missing fields for '{proto_name}': {sorted(missing)}",
            )
        )

    return results
