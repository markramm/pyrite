"""KBSchema - per-KB schema loaded from kb.yaml."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyrite.utils.yaml import load_yaml_file

from .core_types import CORE_TYPES, resolve_type_metadata
from .field_schema import FieldSchema, TypeSchema, _validate_field_value
from .provenance import get_all_relationship_types
from .reserved import RESERVED_FIELD_NAMES
from .validators import validate_date

logger = logging.getLogger(__name__)


@dataclass
class KBSchema:
    """Schema for a knowledge base, loaded from kb.yaml."""

    name: str = ""
    description: str = ""
    kb_type: str = ""
    types: dict[str, TypeSchema] = field(default_factory=dict)
    policies: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 0

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

                # Strip fields that collide with reserved names
                collisions = set(fields.keys()) & RESERVED_FIELD_NAMES
                if collisions:
                    logger.warning(
                        "Type '%s': field names %s collide with reserved names"
                        " and will be ignored",
                        type_name,
                        collisions,
                    )
                    for col_name in collisions:
                        del fields[col_name]

                types[type_name] = TypeSchema(
                    name=type_name,
                    description=type_data.get("description", ""),
                    required=type_data.get("required", ["title"]),
                    optional=type_data.get("optional", []),
                    subdirectory=type_data.get("subdirectory", ""),
                    fields=fields,
                    protocols=type_data.get("protocols", []),
                    layout=type_data.get("layout", ""),
                    ai_instructions=type_data.get("ai_instructions", ""),
                    field_descriptions=type_data.get("field_descriptions", {}),
                    display=type_data.get("display", {}),
                    version=type_data.get("version", 0),
                )
            else:
                types[type_name] = TypeSchema(name=type_name)

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            kb_type=data.get("kb_type", ""),
            types=types,
            policies=data.get("policies", {}),
            validation=data.get("validation", {}),
            schema_version=data.get("schema_version", 0),
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
        entry_sv = (context or {}).get("_schema_version", 0)

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
            # Don't return early -- still run plugin validators below
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
                    if (
                        field_schema.since_version is not None
                        and entry_sv > 0
                        and entry_sv < field_schema.since_version
                    ):
                        warnings.append(
                            {
                                "field": field_name,
                                "rule": "required",
                                "severity": "warning",
                                "expected": "non-empty value",
                                "got": fields.get(field_name),
                                "note": f"Required since version {field_schema.since_version}, entry is version {entry_sv}",
                            }
                        )
                        continue
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
                    if item.get("severity") == "warning":
                        # allow_other fields always produce warnings, not errors
                        warnings.append(item)
                    elif enforce:
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
            from ..plugins import get_registry

            ctx = context or {}
            kb_type = ctx.get("kb_type", "") or self.kb_type
            for validator in get_registry().get_validators_for_kb(kb_type):
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
                        logger.warning(
                            "Validator fallback failed for %s", entry_type, exc_info=True
                        )
                except Exception:
                    logger.warning("Validator execution failed for %s", entry_type, exc_info=True)
        except Exception:
            logger.warning("Schema validation failed for %s", entry_type, exc_info=True)

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
