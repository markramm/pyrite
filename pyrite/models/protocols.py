"""
Entry Protocol Mixins

Composable field protocols for entry types. Each protocol defines a set of
related fields that entry types can opt into via multiple inheritance.

See ADR-0017 for design rationale.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Assignable:
    """Protocol for entries that can be assigned to someone."""

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

    priority: str = ""

    def _prioritizable_to_frontmatter(self) -> dict[str, Any]:
        """Return non-default Prioritizable fields for frontmatter."""
        result: dict[str, Any] = {}
        if self.priority:
            result["priority"] = self.priority
        return result

    @staticmethod
    def _prioritizable_from_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
        """Extract Prioritizable fields from frontmatter dict."""
        return {
            "priority": str(meta.get("priority", "")),
        }


# Registry of protocol name -> mixin class
PROTOCOL_REGISTRY: dict[str, type] = {
    "assignable": Assignable,
    "temporal": Temporal,
    "locatable": Locatable,
    "statusable": Statusable,
    "prioritizable": Prioritizable,
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
}

# Field names promoted to DB columns by IndexManager
PROTOCOL_COLUMN_KEYS: frozenset[str] = frozenset(PROTOCOL_FIELDS.keys())
