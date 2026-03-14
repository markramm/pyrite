"""Tests for edge endpoint query methods (Wave 3A)."""

import pytest

from pyrite.storage.database import PyriteDB


@pytest.fixture
def db_with_edges(tmp_path):
    """DB with entries and edge endpoints for query testing."""
    db = PyriteDB(tmp_path / "index.db")

    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    db.register_kb("test", "standard", str(kb_path))

    # Create entity entries
    db.upsert_entry(
        {"id": "person-1", "kb_name": "test", "title": "Person 1", "entry_type": "person"}
    )
    db.upsert_entry(
        {"id": "company-1", "kb_name": "test", "title": "Company 1", "entry_type": "organization"}
    )
    db.upsert_entry(
        {"id": "company-2", "kb_name": "test", "title": "Company 2", "entry_type": "organization"}
    )

    # Create an ownership edge entry with endpoints
    db.upsert_entry(
        {
            "id": "own-1",
            "kb_name": "test",
            "title": "Ownership 1",
            "entry_type": "ownership",
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

    # Create a membership edge entry
    db.upsert_entry(
        {
            "id": "mem-1",
            "kb_name": "test",
            "title": "Membership 1",
            "entry_type": "membership",
            "_edge_endpoints": [
                {
                    "role": "source",
                    "field_name": "person",
                    "endpoint_id": "person-1",
                    "endpoint_kb": "test",
                    "edge_type": "membership",
                },
                {
                    "role": "target",
                    "field_name": "organization",
                    "endpoint_id": "company-2",
                    "endpoint_kb": "test",
                    "edge_type": "membership",
                },
            ],
        }
    )

    yield db
    db.close()


class TestGetEdgeEndpoints:
    def test_get_edge_endpoints_returns_endpoints(self, db_with_edges):
        """Query edge endpoints for own-1 should return 2 endpoints with correct roles."""
        results = db_with_edges.get_edge_endpoints("own-1", "test")
        assert len(results) == 2
        roles = {r["role"] for r in results}
        assert roles == {"source", "target"}
        # Check field names
        by_role = {r["role"]: r for r in results}
        assert by_role["source"]["field_name"] == "owner"
        assert by_role["source"]["endpoint_id"] == "person-1"
        assert by_role["target"]["field_name"] == "asset"
        assert by_role["target"]["endpoint_id"] == "company-1"
        # Check joined entry info
        assert by_role["source"]["title"] == "Person 1"
        assert by_role["target"]["entry_type"] == "organization"

    def test_get_edge_endpoints_nonexistent_entry(self, db_with_edges):
        """Query for entry with no endpoints should return empty list."""
        results = db_with_edges.get_edge_endpoints("person-1", "test")
        assert results == []


class TestGetEdgesByEndpoint:
    def test_get_edges_by_endpoint_returns_edges(self, db_with_edges):
        """Query edges by endpoint person-1 should return 2 edges (ownership + membership)."""
        results = db_with_edges.get_edges_by_endpoint("person-1", "test")
        assert len(results) == 2
        edge_ids = {r["id"] for r in results}
        assert edge_ids == {"own-1", "mem-1"}

    def test_get_edges_by_endpoint_includes_entry_info(self, db_with_edges):
        """Verify title and entry_type are joined from the entry table."""
        results = db_with_edges.get_edges_by_endpoint("person-1", "test")
        by_id = {r["id"]: r for r in results}
        assert by_id["own-1"]["title"] == "Ownership 1"
        assert by_id["own-1"]["entry_type"] == "ownership"
        assert by_id["mem-1"]["title"] == "Membership 1"
        assert by_id["mem-1"]["entry_type"] == "membership"


class TestGetEdgesBetween:
    def test_get_edges_between_returns_shared_edges(self, db_with_edges):
        """Query edges between person-1 and company-1 should return own-1."""
        results = db_with_edges.get_edges_between("person-1", "company-1", "test")
        assert len(results) == 1
        assert results[0]["id"] == "own-1"
        assert results[0]["title"] == "Ownership 1"

    def test_get_edges_between_no_shared_edges(self, db_with_edges):
        """Query edges between company-1 and company-2 should return empty."""
        results = db_with_edges.get_edges_between("company-1", "company-2", "test")
        assert results == []


class TestPassThroughViaPyriteDB:
    def test_pass_through_via_pyritedb(self, db_with_edges):
        """Verify PyriteDB methods delegate correctly to the backend."""
        # get_edge_endpoints
        eps = db_with_edges.get_edge_endpoints("own-1", "test")
        assert len(eps) == 2

        # get_edges_by_endpoint
        edges = db_with_edges.get_edges_by_endpoint("company-1", "test")
        assert len(edges) == 1
        assert edges[0]["id"] == "own-1"

        # get_edges_between
        between = db_with_edges.get_edges_between("person-1", "company-2", "test")
        assert len(between) == 1
        assert between[0]["id"] == "mem-1"
