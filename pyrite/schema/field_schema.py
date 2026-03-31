"""Field and type schema definitions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .validators import validate_date

if TYPE_CHECKING:
    from ..models import Entry

_TEMPLATE_RE = re.compile(r"\{(\w+)\}")


def expand_subdirectory_template(template: str, entry: Entry) -> str:
    """Expand {field} placeholders in a subdirectory template from entry fields.

    Resolution order for each placeholder:
      1. Dataclass attribute (getattr) — covers core type fields like status, date
      2. entry.metadata[field] — covers GenericEntry custom fields
      3. Fallback to literal "_unknown"

    Enum values are converted via .value. The result is sanitized to prevent
    path traversal (no "..", no leading "/").
    """
    if not template or "{" not in template:
        return template

    def _replace(match: re.Match) -> str:
        field_name = match.group(1)
        value = getattr(entry, field_name, None)
        if value is None:
            md = getattr(entry, "metadata", None)
            if md is not None:
                value = md.get(field_name)
        if value is None:
            return "_unknown"
        if hasattr(value, "value"):
            value = value.value
        s = str(value).strip().lower().replace(" ", "-")
        s = s.replace("..", "").replace("/", "-").strip("-") or "_unknown"
        return s

    result = _TEMPLATE_RE.sub(_replace, template)
    return result.lstrip("/")


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
    allow_other: bool = (
        False  # when True, unknown select/multi-select values produce warnings not errors
    )
    items: dict[str, Any] = field(default_factory=dict)  # for list type
    constraints: dict[str, Any] = field(default_factory=dict)  # min, max, format, target_type
    since_version: int | None = None

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
    def from_dict(cls, name: str, data: dict[str, Any]) -> FieldSchema:
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
            allow_other=data.get("allow_other", False),
            items=data.get("items", {}),
            constraints=constraints,
            since_version=data.get("since_version"),
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
        if self.allow_other:
            result["allow_other"] = True
        if self.items:
            result["items"] = self.items
        if self.since_version is not None:
            result["since_version"] = self.since_version
        result.update(self.constraints)
        return result


@dataclass
class EndpointSpec:
    """Schema for an edge-type endpoint."""

    field: str  # which entry field maps to this endpoint
    accepts: list[str] = field(default_factory=list)  # accepted entry types


@dataclass
class TypeSchema:
    """Schema definition for an entry type (core or custom)."""

    name: str
    description: str = ""
    required: list[str] = field(default_factory=lambda: ["title"])
    optional: list[str] = field(default_factory=list)
    subdirectory: str = ""
    file_pattern: str = ""  # e.g. "{date}--{slug}.md" for custom filenames
    fields: dict[str, FieldSchema] = field(default_factory=dict)
    protocols: list[str] = field(default_factory=list)  # ADR-0017: e.g. ["temporal", "assignable"]
    layout: str = ""  # "document" or "record"
    ai_instructions: str = ""
    field_descriptions: dict[str, str] = field(default_factory=dict)
    display: dict[str, Any] = field(default_factory=dict)
    version: int = 0
    guidelines: str = ""  # Contributing standards, quality expectations
    goals: str = ""  # What entries of this type should achieve
    evaluation_rubric: list[str | dict[str, Any]] = field(
        default_factory=list
    )  # Assertions for QA validation
    edge_type: bool = False  # Whether this type represents an edge/relationship
    endpoints: dict[str, EndpointSpec] = field(default_factory=dict)  # Edge endpoint specs

    def resolve_subdirectory(self, entry: Entry) -> str:
        """Return the resolved subdirectory, expanding template placeholders."""
        if not self.subdirectory:
            return ""
        return expand_subdirectory_template(self.subdirectory, entry)

    def resolve_filename(self, entry: Entry) -> str | None:
        """Return a custom filename for the entry, or None to use default.

        Supported placeholders:
          - ``{id}`` — entry ID
          - ``{slug}`` — entry ID (alias)
          - ``{date}`` — entry date field (YYYY-MM-DD)
          - ``{title}`` — slugified title
          - ``{type}`` — entry type

        Example: ``file_pattern: "{date}--{slug}.md"``
        """
        if not self.file_pattern:
            return None
        from ..schema import generate_entry_id

        replacements = {
            "id": entry.id,
            "slug": entry.id,
            "date": getattr(entry, "date", "") or "",
            "title": generate_entry_id(entry.title),
            "type": entry.entry_type,
        }
        try:
            return self.file_pattern.format(**replacements)
        except (KeyError, IndexError):
            return None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"description": self.description}
        if self.required != ["title"]:
            result["required"] = self.required
        if self.optional:
            result["optional"] = self.optional
        if self.subdirectory:
            result["subdirectory"] = self.subdirectory
        if self.file_pattern:
            result["file_pattern"] = self.file_pattern
        if self.fields:
            result["fields"] = {name: fs.to_dict() for name, fs in self.fields.items()}
        if self.protocols:
            result["protocols"] = self.protocols
        if self.layout:
            result["layout"] = self.layout
        if self.ai_instructions:
            result["ai_instructions"] = self.ai_instructions
        if self.field_descriptions:
            result["field_descriptions"] = self.field_descriptions
        if self.display:
            result["display"] = self.display
        if self.version > 0:
            result["version"] = self.version
        if self.guidelines:
            result["guidelines"] = self.guidelines
        if self.goals:
            result["goals"] = self.goals
        if self.evaluation_rubric:
            result["evaluation_rubric"] = self.evaluation_rubric
        if self.edge_type:
            result["edge_type"] = True
        if self.endpoints:
            result["endpoints"] = {
                role: {"field": ep.field, "accepts": ep.accepts}
                for role, ep in self.endpoints.items()
            }
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
            err = {
                "field": field_name,
                "rule": "field_select",
                "expected": field_schema.options,
                "got": value,
            }
            if field_schema.allow_other:
                err["severity"] = "warning"
            errors.append(err)

    elif ft == "multi-select":
        if isinstance(value, list) and field_schema.options:
            invalid = [v for v in value if v not in field_schema.options]
            if invalid:
                err = {
                    "field": field_name,
                    "rule": "field_multi_select",
                    "expected": field_schema.options,
                    "got": invalid,
                }
                if field_schema.allow_other:
                    err["severity"] = "warning"
                errors.append(err)
        elif not isinstance(value, list):
            errors.append(
                {
                    "field": field_name,
                    "rule": "field_multi_select",
                    "expected": "list",
                    "got": type(value).__name__,
                }
            )

    # text, object-ref, list, tags -- no validation beyond presence (for now)

    return errors
