"""Field and type schema definitions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .validators import validate_date


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
class TypeSchema:
    """Schema definition for an entry type (core or custom)."""

    name: str
    description: str = ""
    required: list[str] = field(default_factory=lambda: ["title"])
    optional: list[str] = field(default_factory=list)
    subdirectory: str = ""
    fields: dict[str, FieldSchema] = field(default_factory=dict)
    protocols: list[str] = field(default_factory=list)  # ADR-0017: e.g. ["temporal", "assignable"]
    layout: str = ""  # "document" or "record"
    ai_instructions: str = ""
    field_descriptions: dict[str, str] = field(default_factory=dict)
    display: dict[str, Any] = field(default_factory=dict)
    version: int = 0

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
