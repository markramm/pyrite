"""Tests for the list_edge_types MCP tool."""

import pytest

from pyrite.schema.field_schema import EndpointSpec, TypeSchema
from pyrite.schema.kb_schema import KBSchema


class TestListEdgeTypes:
    def test_returns_edge_types_from_schema(self):
        """Verify edge type info is correctly extracted from KB schema."""
        schema = KBSchema.from_dict(
            {
                "types": {
                    "ownership": {
                        "description": "Ownership relationship",
                        "edge_type": True,
                        "endpoints": {
                            "source": {"field": "owner", "accepts": ["person", "organization"]},
                            "target": {"field": "asset", "accepts": ["organization", "asset"]},
                        },
                    },
                    "note": {
                        "description": "A note",
                    },
                },
            }
        )

        # Verify edge types can be filtered from schema
        edge_types = []
        for type_name, type_schema in schema.types.items():
            if getattr(type_schema, "edge_type", False):
                edge_types.append(type_name)

        assert edge_types == ["ownership"]
        assert schema.types["ownership"].edge_type is True
        assert "source" in schema.types["ownership"].endpoints
        assert schema.types["ownership"].endpoints["source"].field == "owner"
        assert schema.types["ownership"].endpoints["source"].accepts == [
            "person",
            "organization",
        ]

    def test_non_edge_types_excluded(self):
        schema = KBSchema.from_dict(
            {
                "types": {
                    "note": {"description": "A note"},
                    "person": {"description": "A person"},
                },
            }
        )
        edge_types = [name for name, ts in schema.types.items() if getattr(ts, "edge_type", False)]
        assert edge_types == []

    def test_multiple_edge_types(self):
        schema = KBSchema.from_dict(
            {
                "types": {
                    "ownership": {
                        "description": "Ownership",
                        "edge_type": True,
                        "endpoints": {
                            "source": {"field": "owner", "accepts": ["person"]},
                            "target": {"field": "asset", "accepts": ["asset"]},
                        },
                    },
                    "membership": {
                        "description": "Membership",
                        "edge_type": True,
                        "endpoints": {
                            "source": {"field": "person", "accepts": ["person"]},
                            "target": {
                                "field": "organization",
                                "accepts": ["organization"],
                            },
                        },
                    },
                },
            }
        )
        edge_types = [name for name, ts in schema.types.items() if getattr(ts, "edge_type", False)]
        assert len(edge_types) == 2

    def test_edge_type_endpoint_accepts_list(self):
        """Verify endpoint accepts is a list of accepted entry types."""
        schema = KBSchema.from_dict(
            {
                "types": {
                    "funding": {
                        "description": "Funding relationship",
                        "edge_type": True,
                        "endpoints": {
                            "source": {
                                "field": "funder",
                                "accepts": ["person", "organization", "government"],
                            },
                            "target": {
                                "field": "recipient",
                                "accepts": ["organization", "project"],
                            },
                        },
                    },
                },
            }
        )
        ts = schema.types["funding"]
        assert ts.edge_type is True
        assert ts.endpoints["source"].accepts == [
            "person",
            "organization",
            "government",
        ]
        assert ts.endpoints["target"].field == "recipient"
