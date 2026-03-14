"""Tests for JI plugin edge-type declarations integration."""

import pytest
from pyrite.schema.kb_schema import KBSchema


class TestJIPresetEdgeTypes:
    """Verify JI preset declares edge types correctly."""

    @pytest.fixture
    def ji_schema(self):
        """Load JI preset as a KBSchema."""
        from pyrite_journalism_investigation.preset import JOURNALISM_INVESTIGATION_PRESET

        return KBSchema.from_dict(JOURNALISM_INVESTIGATION_PRESET)

    def test_ownership_is_edge_type(self, ji_schema):
        ts = ji_schema.types.get("ownership")
        assert ts is not None
        assert ts.edge_type is True
        assert "source" in ts.endpoints
        assert "target" in ts.endpoints

    def test_ownership_source_endpoint(self, ji_schema):
        ep = ji_schema.types["ownership"].endpoints["source"]
        assert ep.field == "owner"
        assert "person" in ep.accepts
        assert "organization" in ep.accepts

    def test_ownership_target_endpoint(self, ji_schema):
        ep = ji_schema.types["ownership"].endpoints["target"]
        assert ep.field == "asset"
        assert "organization" in ep.accepts
        assert "asset" in ep.accepts
        assert "account" in ep.accepts

    def test_membership_is_edge_type(self, ji_schema):
        ts = ji_schema.types.get("membership")
        assert ts is not None
        assert ts.edge_type is True
        assert ts.endpoints["source"].field == "person"
        assert ts.endpoints["target"].field == "organization"

    def test_membership_source_accepts(self, ji_schema):
        ep = ji_schema.types["membership"].endpoints["source"]
        assert "person" in ep.accepts

    def test_membership_target_accepts(self, ji_schema):
        ep = ji_schema.types["membership"].endpoints["target"]
        assert "organization" in ep.accepts

    def test_funding_is_edge_type(self, ji_schema):
        ts = ji_schema.types.get("funding")
        assert ts is not None
        assert ts.edge_type is True
        assert ts.endpoints["source"].field == "funder"
        assert ts.endpoints["target"].field == "recipient"

    def test_funding_source_accepts(self, ji_schema):
        ep = ji_schema.types["funding"].endpoints["source"]
        assert "person" in ep.accepts
        assert "organization" in ep.accepts

    def test_funding_target_accepts(self, ji_schema):
        ep = ji_schema.types["funding"].endpoints["target"]
        assert "person" in ep.accepts
        assert "organization" in ep.accepts

    def test_non_connection_types_not_edge(self, ji_schema):
        """Event, entity, and other types should NOT be edge types."""
        for type_name in ["person", "organization", "investigation_event", "note", "claim"]:
            ts = ji_schema.types.get(type_name)
            if ts:
                assert not getattr(ts, "edge_type", False), (
                    f"{type_name} should not be an edge type"
                )

    def test_all_three_connection_types_are_edges(self, ji_schema):
        edge_types = [
            name for name, ts in ji_schema.types.items() if getattr(ts, "edge_type", False)
        ]
        assert set(edge_types) == {"ownership", "membership", "funding"}


class TestJIEdgeEndpointPipeline:
    """Test that JI connection entries populate edge_endpoints via index sync."""

    def test_ownership_entry_creates_edge_endpoints(self, tmp_path):
        """When an ownership entry is indexed with edge_type schema, endpoints are stored."""
        from pyrite.storage.database import PyriteDB

        kb_path = tmp_path / "test-kb"
        kb_path.mkdir()

        db = PyriteDB(tmp_path / "index.db")
        db.register_kb("test", "standard", str(kb_path))

        # Create entity entries
        db.upsert_entry(
            {"id": "person-1", "kb_name": "test", "title": "Person 1", "entry_type": "person"}
        )
        db.upsert_entry(
            {
                "id": "company-1",
                "kb_name": "test",
                "title": "Company 1",
                "entry_type": "organization",
            }
        )

        # Create ownership entry WITH edge endpoints (simulating what IndexManager does)
        db.upsert_entry(
            {
                "id": "own-1",
                "kb_name": "test",
                "title": "Person 1 owns Company 1",
                "entry_type": "ownership",
                "metadata": {
                    "owner": "[[person-1]]",
                    "asset": "[[company-1]]",
                    "percentage": 51,
                },
                "_edge_endpoints": [
                    {
                        "role": "source",
                        "field_name": "owner",
                        "endpoint_id": "person-1",
                        "endpoint_kb": "test",
                        "edge_type": "ownership",
                    },
                    {
                        "role": "target",
                        "field_name": "asset",
                        "endpoint_id": "company-1",
                        "endpoint_kb": "test",
                        "edge_type": "ownership",
                    },
                ],
            }
        )

        # Verify edge endpoints stored
        endpoints = db.get_edge_endpoints("own-1", "test")
        assert len(endpoints) == 2
        roles = {ep["role"] for ep in endpoints}
        assert roles == {"source", "target"}

        # Verify reverse query
        edges = db.get_edges_by_endpoint("person-1", "test")
        assert len(edges) == 1
        assert edges[0]["id"] == "own-1"

        edges_between = db.get_edges_between("person-1", "company-1", "test")
        assert len(edges_between) == 1

        db.close()

    def test_membership_entry_creates_edge_endpoints(self, tmp_path):
        """Membership edge endpoints are stored and queryable."""
        from pyrite.storage.database import PyriteDB

        db = PyriteDB(tmp_path / "index.db")
        kb_path = tmp_path / "test-kb"
        kb_path.mkdir()
        db.register_kb("test", "standard", str(kb_path))

        db.upsert_entry(
            {"id": "person-a", "kb_name": "test", "title": "Alice", "entry_type": "person"}
        )
        db.upsert_entry(
            {"id": "org-b", "kb_name": "test", "title": "Acme Corp", "entry_type": "organization"}
        )

        db.upsert_entry(
            {
                "id": "mem-1",
                "kb_name": "test",
                "title": "Alice member of Acme Corp",
                "entry_type": "membership",
                "_edge_endpoints": [
                    {
                        "role": "source",
                        "field_name": "person",
                        "endpoint_id": "person-a",
                        "endpoint_kb": "test",
                        "edge_type": "membership",
                    },
                    {
                        "role": "target",
                        "field_name": "organization",
                        "endpoint_id": "org-b",
                        "endpoint_kb": "test",
                        "edge_type": "membership",
                    },
                ],
            }
        )

        endpoints = db.get_edge_endpoints("mem-1", "test")
        assert len(endpoints) == 2

        edges = db.get_edges_by_endpoint("org-b", "test")
        assert len(edges) == 1
        assert edges[0]["id"] == "mem-1"

        db.close()

    def test_funding_entry_creates_edge_endpoints(self, tmp_path):
        """Funding edge endpoints are stored and queryable."""
        from pyrite.storage.database import PyriteDB

        db = PyriteDB(tmp_path / "index.db")
        kb_path = tmp_path / "test-kb"
        kb_path.mkdir()
        db.register_kb("test", "standard", str(kb_path))

        db.upsert_entry(
            {"id": "org-x", "kb_name": "test", "title": "Funder Org", "entry_type": "organization"}
        )
        db.upsert_entry(
            {
                "id": "org-y",
                "kb_name": "test",
                "title": "Recipient Org",
                "entry_type": "organization",
            }
        )

        db.upsert_entry(
            {
                "id": "fund-1",
                "kb_name": "test",
                "title": "Funder Org funds Recipient Org",
                "entry_type": "funding",
                "_edge_endpoints": [
                    {
                        "role": "source",
                        "field_name": "funder",
                        "endpoint_id": "org-x",
                        "endpoint_kb": "test",
                        "edge_type": "funding",
                    },
                    {
                        "role": "target",
                        "field_name": "recipient",
                        "endpoint_id": "org-y",
                        "endpoint_kb": "test",
                        "edge_type": "funding",
                    },
                ],
            }
        )

        endpoints = db.get_edge_endpoints("fund-1", "test")
        assert len(endpoints) == 2

        edges_between = db.get_edges_between("org-x", "org-y", "test")
        assert len(edges_between) == 1
        assert edges_between[0]["id"] == "fund-1"

        db.close()
