"""
Tests for Schema-as-Config: Rich Field Types (ADR-0008).

Tests the FieldSchema, extended TypeSchema, and field-level validation.
"""

import pytest

from pyrite.schema import FieldSchema, KBSchema, TypeSchema

# =============================================================================
# FieldSchema Parsing
# =============================================================================


class TestFieldSchemaFromDict:
    """Test FieldSchema.from_dict() parses field definitions from kb.yaml."""

    def test_text_field_minimal(self):
        field = FieldSchema.from_dict("name", {"type": "text"})
        assert field.name == "name"
        assert field.field_type == "text"
        assert field.required is False
        assert field.default is None
        assert field.description == ""

    def test_text_field_with_constraints(self):
        field = FieldSchema.from_dict(
            "email",
            {"type": "text", "required": True, "format": "email", "description": "Contact email"},
        )
        assert field.name == "email"
        assert field.field_type == "text"
        assert field.required is True
        assert field.constraints == {"format": "email"}
        assert field.description == "Contact email"

    def test_number_field_with_range(self):
        field = FieldSchema.from_dict("priority", {"type": "number", "min": 1, "max": 10})
        assert field.field_type == "number"
        assert field.constraints == {"min": 1, "max": 10}

    def test_date_field(self):
        field = FieldSchema.from_dict("due_date", {"type": "date", "required": True})
        assert field.field_type == "date"
        assert field.required is True

    def test_datetime_field(self):
        field = FieldSchema.from_dict("timestamp", {"type": "datetime"})
        assert field.field_type == "datetime"

    def test_checkbox_field(self):
        field = FieldSchema.from_dict("active", {"type": "checkbox", "default": True})
        assert field.field_type == "checkbox"
        assert field.default is True

    def test_select_field(self):
        field = FieldSchema.from_dict(
            "status",
            {
                "type": "select",
                "options": ["draft", "review", "published"],
                "default": "draft",
            },
        )
        assert field.field_type == "select"
        assert field.options == ["draft", "review", "published"]
        assert field.default == "draft"

    def test_multi_select_field(self):
        field = FieldSchema.from_dict(
            "categories",
            {"type": "multi-select", "options": ["tech", "science", "politics"]},
        )
        assert field.field_type == "multi-select"
        assert field.options == ["tech", "science", "politics"]

    def test_object_ref_field(self):
        field = FieldSchema.from_dict(
            "assignee",
            {"type": "object-ref", "target_type": "person"},
        )
        assert field.field_type == "object-ref"
        assert field.constraints == {"target_type": "person"}

    def test_list_field_with_items(self):
        field = FieldSchema.from_dict(
            "attendees",
            {
                "type": "list",
                "items": {"type": "object-ref", "target_type": "person"},
            },
        )
        assert field.field_type == "list"
        assert field.items == {"type": "object-ref", "target_type": "person"}

    def test_tags_field(self):
        field = FieldSchema.from_dict("labels", {"type": "tags"})
        assert field.field_type == "tags"

    def test_field_to_dict_round_trip(self):
        original = {
            "type": "select",
            "required": True,
            "options": ["a", "b", "c"],
            "default": "a",
            "description": "Pick one",
        }
        field = FieldSchema.from_dict("choice", original)
        result = field.to_dict()
        assert result["type"] == "select"
        assert result["required"] is True
        assert result["options"] == ["a", "b", "c"]
        assert result["default"] == "a"
        assert result["description"] == "Pick one"


# =============================================================================
# TypeSchema with Fields
# =============================================================================


class TestTypeSchemaWithFields:
    """Test TypeSchema extended with FieldSchema definitions."""

    def test_type_schema_with_fields(self):
        ts = TypeSchema(
            name="meeting",
            description="Meeting notes",
            fields={
                "date": FieldSchema(name="date", field_type="date", required=True),
                "status": FieldSchema(
                    name="status",
                    field_type="select",
                    options=["scheduled", "completed", "cancelled"],
                    default="scheduled",
                ),
            },
            layout="record",
        )
        assert ts.name == "meeting"
        assert ts.layout == "record"
        assert len(ts.fields) == 2
        assert ts.fields["date"].required is True
        assert ts.fields["status"].options == ["scheduled", "completed", "cancelled"]

    def test_type_schema_to_dict_includes_fields(self):
        ts = TypeSchema(
            name="contact",
            description="A contact",
            fields={
                "email": FieldSchema(
                    name="email", field_type="text", constraints={"format": "email"}
                ),
            },
            layout="record",
        )
        d = ts.to_dict()
        assert "fields" in d
        assert "email" in d["fields"]
        assert d["fields"]["email"]["type"] == "text"
        assert d["layout"] == "record"

    def test_type_schema_to_dict_omits_empty_fields(self):
        ts = TypeSchema(name="note", description="A note")
        d = ts.to_dict()
        assert "fields" not in d
        assert "layout" not in d

    def test_type_schema_backward_compatible(self):
        """TypeSchema without fields works exactly as before."""
        ts = TypeSchema(name="note", required=["title", "tags"])
        assert ts.fields == {}
        assert ts.layout == ""
        assert ts.required == ["title", "tags"]


# =============================================================================
# KBSchema Parsing with Fields
# =============================================================================


class TestKBSchemaFieldParsing:
    """Test KBSchema.from_dict() parsing of rich field definitions."""

    def test_parse_type_with_fields(self):
        data = {
            "name": "test-kb",
            "types": {
                "meeting": {
                    "description": "Meeting notes",
                    "layout": "record",
                    "fields": {
                        "date": {"type": "date", "required": True},
                        "attendees": {
                            "type": "list",
                            "items": {"type": "object-ref", "target_type": "person"},
                        },
                        "status": {
                            "type": "select",
                            "options": ["scheduled", "completed", "cancelled"],
                            "default": "scheduled",
                        },
                    },
                    "subdirectory": "meetings",
                }
            },
        }
        schema = KBSchema.from_dict(data)
        assert "meeting" in schema.types
        ts = schema.types["meeting"]
        assert ts.layout == "record"
        assert len(ts.fields) == 3
        assert ts.fields["date"].required is True
        assert ts.fields["status"].options == ["scheduled", "completed", "cancelled"]
        assert ts.fields["attendees"].field_type == "list"

    def test_parse_type_without_fields_backward_compat(self):
        """Types without field definitions still work."""
        data = {
            "name": "test-kb",
            "types": {
                "custom": {
                    "description": "A custom type",
                    "required": ["title", "category"],
                    "subdirectory": "customs",
                }
            },
        }
        schema = KBSchema.from_dict(data)
        ts = schema.types["custom"]
        assert ts.fields == {}
        assert ts.required == ["title", "category"]

    def test_parse_mixed_types(self):
        """KB can have both field-rich and simple types."""
        data = {
            "name": "mixed",
            "types": {
                "meeting": {
                    "description": "With fields",
                    "fields": {
                        "date": {"type": "date"},
                    },
                },
                "note": {
                    "description": "Simple type",
                    "required": ["title"],
                },
            },
        }
        schema = KBSchema.from_dict(data)
        assert len(schema.types["meeting"].fields) == 1
        assert schema.types["note"].fields == {}


# =============================================================================
# Field-Level Validation
# =============================================================================


class TestFieldValidation:
    """Test field-level validation via KBSchema.validate_entry()."""

    @pytest.fixture()
    def schema_with_fields(self):
        return KBSchema.from_dict(
            {
                "name": "test",
                "validation": {"enforce": True},
                "types": {
                    "task": {
                        "description": "A task",
                        "fields": {
                            "title": {"type": "text", "required": True},
                            "priority": {"type": "number", "min": 1, "max": 5},
                            "due_date": {"type": "date"},
                            "status": {
                                "type": "select",
                                "options": ["todo", "doing", "done"],
                            },
                            "categories": {
                                "type": "multi-select",
                                "options": ["bug", "feature", "docs"],
                            },
                            "active": {"type": "checkbox"},
                            "assignee": {"type": "object-ref", "target_type": "person"},
                        },
                    }
                },
            }
        )

    def test_valid_entry_passes(self, schema_with_fields):
        result = schema_with_fields.validate_entry(
            "task",
            {
                "title": "Fix the bug",
                "priority": 3,
                "status": "todo",
                "due_date": "2026-03-15",
                "active": True,
            },
        )
        assert result["valid"] is True
        assert result["errors"] == []

    def test_required_field_missing(self, schema_with_fields):
        result = schema_with_fields.validate_entry("task", {"priority": 3})
        assert result["valid"] is False
        errors = result["errors"]
        field_names = [e["field"] for e in errors]
        assert "title" in field_names

    def test_number_out_of_range(self, schema_with_fields):
        result = schema_with_fields.validate_entry(
            "task",
            {
                "title": "Test",
                "priority": 10,
            },
        )
        assert result["valid"] is False
        errors = result["errors"]
        assert any(e["field"] == "priority" and e["rule"] == "field_range" for e in errors)

    def test_number_below_range(self, schema_with_fields):
        result = schema_with_fields.validate_entry(
            "task",
            {
                "title": "Test",
                "priority": 0,
            },
        )
        assert result["valid"] is False

    def test_invalid_date(self, schema_with_fields):
        result = schema_with_fields.validate_entry(
            "task",
            {
                "title": "Test",
                "due_date": "not-a-date",
            },
        )
        assert result["valid"] is False
        assert any(e["field"] == "due_date" and e["rule"] == "field_date" for e in result["errors"])

    def test_select_invalid_option(self, schema_with_fields):
        result = schema_with_fields.validate_entry(
            "task",
            {
                "title": "Test",
                "status": "invalid",
            },
        )
        assert result["valid"] is False
        errors = result["errors"]
        assert any(e["field"] == "status" and e["rule"] == "field_select" for e in errors)

    def test_select_valid_option(self, schema_with_fields):
        result = schema_with_fields.validate_entry(
            "task",
            {
                "title": "Test",
                "status": "doing",
            },
        )
        assert result["valid"] is True

    def test_multi_select_invalid_option(self, schema_with_fields):
        result = schema_with_fields.validate_entry(
            "task",
            {
                "title": "Test",
                "categories": ["bug", "invalid"],
            },
        )
        assert result["valid"] is False
        errors = result["errors"]
        assert any(e["field"] == "categories" and e["rule"] == "field_multi_select" for e in errors)

    def test_multi_select_valid(self, schema_with_fields):
        result = schema_with_fields.validate_entry(
            "task",
            {
                "title": "Test",
                "categories": ["bug", "docs"],
            },
        )
        assert result["valid"] is True

    def test_checkbox_non_bool(self, schema_with_fields):
        result = schema_with_fields.validate_entry(
            "task",
            {
                "title": "Test",
                "active": "yes",
            },
        )
        assert result["valid"] is False
        errors = result["errors"]
        assert any(e["field"] == "active" and e["rule"] == "field_checkbox" for e in errors)

    def test_missing_optional_fields_ok(self, schema_with_fields):
        """Fields without required=True are optional."""
        result = schema_with_fields.validate_entry("task", {"title": "Just a title"})
        assert result["valid"] is True

    def test_unknown_fields_ignored(self, schema_with_fields):
        """Extra fields not in schema are allowed (metadata passthrough)."""
        result = schema_with_fields.validate_entry(
            "task",
            {
                "title": "Test",
                "unknown_field": "some value",
            },
        )
        assert result["valid"] is True

    def test_fields_not_enforced_when_enforce_false(self):
        """When enforce=False, field validation produces warnings not errors."""
        schema = KBSchema.from_dict(
            {
                "name": "test",
                "validation": {"enforce": False},
                "types": {
                    "task": {
                        "description": "A task",
                        "fields": {
                            "status": {
                                "type": "select",
                                "options": ["todo", "done"],
                            },
                        },
                    }
                },
            }
        )
        result = schema.validate_entry("task", {"title": "Test", "status": "invalid"})
        # With enforce=False, field violations are warnings
        assert result["valid"] is True
        assert len(result["warnings"]) > 0


# =============================================================================
# Agent Schema Export
# =============================================================================


class TestAgentSchemaWithFields:
    """Test to_agent_schema() includes field type information."""

    def test_custom_type_fields_in_agent_schema(self):
        schema = KBSchema.from_dict(
            {
                "name": "test",
                "types": {
                    "meeting": {
                        "description": "Meeting notes",
                        "layout": "record",
                        "fields": {
                            "date": {
                                "type": "date",
                                "required": True,
                                "description": "When the meeting occurred",
                            },
                            "status": {
                                "type": "select",
                                "options": ["scheduled", "completed"],
                            },
                        },
                    }
                },
            }
        )
        agent = schema.to_agent_schema()
        meeting = agent["types"]["meeting"]
        assert "fields" in meeting
        assert meeting["fields"]["date"]["type"] == "date"
        assert meeting["fields"]["date"]["required"] is True
        assert meeting["fields"]["date"]["description"] == "When the meeting occurred"
        assert meeting["fields"]["status"]["options"] == ["scheduled", "completed"]

    def test_core_types_still_present(self):
        schema = KBSchema.from_dict({"name": "test"})
        agent = schema.to_agent_schema()
        assert "note" in agent["types"]
        assert "person" in agent["types"]
        assert "event" in agent["types"]
