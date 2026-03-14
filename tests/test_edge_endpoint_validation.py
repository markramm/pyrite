"""Tests for edge-type endpoint validation in KBSchema.validate_entry().

Wave 1C: Validates that edge-type entries have their required endpoint
fields present and non-empty.
"""

from pyrite.schema.field_schema import EndpointSpec, TypeSchema
from pyrite.schema.kb_schema import KBSchema


def _make_edge_schema(**extra_type_data):
    """Build a KBSchema with an edge type that has two endpoints."""
    data = {
        "name": "test",
        "kb_type": "generic",
        "validation": {"enforce": True},
        "types": {
            "authored_by": {
                "description": "Authorship edge",
                "edge_type": True,
                "endpoints": {
                    "source": {"field": "document_id", "accepts": ["document"]},
                    "target": {"field": "author_id", "accepts": ["person"]},
                },
                **extra_type_data,
            }
        },
    }
    return KBSchema.from_dict(data)


class TestEdgeEndpointValidation:
    """Tests for edge_endpoint_required validation rule."""

    def test_edge_type_all_endpoints_present_passes(self):
        """Edge-type entry with all endpoints present passes validation."""
        schema = _make_edge_schema()
        result = schema.validate_entry(
            "authored_by",
            {
                "title": "Doc authored by Alice",
                "document_id": "doc-001",
                "author_id": "person-alice",
            },
        )
        endpoint_errors = [
            e for e in result["errors"] if e.get("rule") == "edge_endpoint_required"
        ]
        assert endpoint_errors == []

    def test_edge_type_missing_endpoint_produces_error(self):
        """Edge-type entry missing an endpoint field produces an error."""
        schema = _make_edge_schema()
        result = schema.validate_entry(
            "authored_by",
            {
                "title": "Doc authored by unknown",
                "document_id": "doc-001",
                # author_id is missing
            },
        )
        endpoint_errors = [
            e for e in result["errors"] if e.get("rule") == "edge_endpoint_required"
        ]
        assert len(endpoint_errors) == 1
        assert endpoint_errors[0]["field"] == "author_id"
        assert endpoint_errors[0]["got"] is None

    def test_edge_type_missing_multiple_endpoints_produces_multiple_errors(self):
        """Edge-type entry missing multiple endpoint fields produces multiple errors."""
        schema = _make_edge_schema()
        result = schema.validate_entry(
            "authored_by",
            {
                "title": "Incomplete edge",
                # both document_id and author_id are missing
            },
        )
        endpoint_errors = [
            e for e in result["errors"] if e.get("rule") == "edge_endpoint_required"
        ]
        assert len(endpoint_errors) == 2
        error_fields = {e["field"] for e in endpoint_errors}
        assert error_fields == {"document_id", "author_id"}

    def test_non_edge_type_not_affected(self):
        """Non-edge-type entry is not affected by endpoint validation."""
        schema = KBSchema.from_dict(
            {
                "name": "test",
                "kb_type": "generic",
                "validation": {"enforce": True},
                "types": {
                    "note": {
                        "description": "A plain note",
                    }
                },
            }
        )
        result = schema.validate_entry(
            "note",
            {"title": "Just a note"},
        )
        endpoint_errors = [
            e for e in result["errors"] if e.get("rule") == "edge_endpoint_required"
        ]
        assert endpoint_errors == []

    def test_edge_type_empty_string_endpoint_produces_error(self):
        """Edge-type entry with empty string endpoint value produces an error."""
        schema = _make_edge_schema()
        result = schema.validate_entry(
            "authored_by",
            {
                "title": "Doc with empty author",
                "document_id": "doc-001",
                "author_id": "",  # empty string
            },
        )
        endpoint_errors = [
            e for e in result["errors"] if e.get("rule") == "edge_endpoint_required"
        ]
        assert len(endpoint_errors) == 1
        assert endpoint_errors[0]["field"] == "author_id"
        assert endpoint_errors[0]["got"] == ""
