"""
Tests for QA REST API endpoints.
"""

import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import EventEntry
from pyrite.server.api import create_app
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository


@pytest.fixture
def qa_env():
    """Create test environment with sample data including entries with QA issues."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"

        events_path = tmpdir / "events"
        events_path.mkdir()

        events_kb = KBConfig(
            name="test-events",
            path=events_path,
            kb_type=KBType.EVENTS,
        )

        config = PyriteConfig(
            knowledge_bases=[events_kb], settings=Settings(index_path=db_path)
        )

        # Create some good entries
        events_repo = KBRepository(events_kb)
        for i in range(3):
            event = EventEntry.create(
                date=f"2025-01-{10+i:02d}",
                title=f"Test Event {i}",
                body=f"Body for event {i} about immigration policy.",
                importance=5 + i,
            )
            event.tags = ["test"]
            events_repo.save(event)

        # Create an entry with an empty body (will trigger empty_body warning)
        empty_body_event = EventEntry.create(
            date="2025-02-01",
            title="Empty Body Event",
            body="",
            importance=3,
        )
        empty_body_event.tags = ["test"]
        events_repo.save(empty_body_event)

        db = PyriteDB(db_path)
        index_mgr = IndexManager(db, config)
        index_mgr.index_all()

        # Inject into app globals
        import pyrite.server.api as api_module

        api_module._config = config
        api_module._db = db
        api_module._index_mgr = index_mgr

        app = create_app(config)
        client = TestClient(app)

        yield {
            "client": client,
            "config": config,
            "db": db,
            "events_kb": events_kb,
        }

        db.close()

        # Reset globals
        api_module._config = None
        api_module._db = None
        api_module._index_mgr = None


class TestQAStatusEndpoint:
    """Test GET /api/qa/status."""

    def test_status_returns_summary(self, qa_env):
        client = qa_env["client"]
        response = client.get("/api/qa/status")
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert "total_issues" in data
        assert "issues_by_severity" in data
        assert "issues_by_rule" in data
        assert data["total_entries"] >= 4

    def test_status_filtered_by_kb(self, qa_env):
        client = qa_env["client"]
        response = client.get("/api/qa/status?kb=test-events")
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert "total_issues" in data
        assert data["total_entries"] >= 4


class TestQAValidateEndpoint:
    """Test GET /api/qa/validate and GET /api/qa/validate/{entry_id}."""

    def test_validate_kb(self, qa_env):
        client = qa_env["client"]
        response = client.get("/api/qa/validate?kb=test-events")
        assert response.status_code == 200
        data = response.json()
        assert "kb_name" in data
        assert "issues" in data
        assert "total" in data
        assert data["kb_name"] == "test-events"

    def test_validate_all_kbs(self, qa_env):
        client = qa_env["client"]
        response = client.get("/api/qa/validate")
        assert response.status_code == 200
        data = response.json()
        assert "kbs" in data
        assert len(data["kbs"]) >= 1

    def test_validate_entry(self, qa_env):
        client = qa_env["client"]
        # Find an entry ID from the DB
        db = qa_env["db"]
        row = db._raw_conn.execute(
            "SELECT id FROM entry WHERE kb_name = 'test-events' LIMIT 1"
        ).fetchone()
        assert row is not None
        entry_id = row["id"]

        response = client.get(f"/api/qa/validate/{entry_id}?kb=test-events")
        assert response.status_code == 200
        data = response.json()
        assert data["entry_id"] == entry_id
        assert data["kb_name"] == "test-events"
        assert "issues" in data

    def test_validate_entry_not_found(self, qa_env):
        client = qa_env["client"]
        response = client.get("/api/qa/validate/nonexistent-entry?kb=test-events")
        assert response.status_code == 200
        data = response.json()
        assert data["entry_id"] == "nonexistent-entry"
        # Should have an entry_not_found issue
        assert any(i["rule"] == "entry_not_found" for i in data["issues"])

    def test_validate_entry_requires_kb(self, qa_env):
        client = qa_env["client"]
        response = client.get("/api/qa/validate/some-entry")
        assert response.status_code == 422  # Missing required kb param


class TestQACoverageEndpoint:
    """Test GET /api/qa/coverage."""

    def test_coverage_returns_stats(self, qa_env):
        client = qa_env["client"]
        response = client.get("/api/qa/coverage?kb=test-events")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "assessed" in data
        assert "unassessed" in data
        assert "coverage_pct" in data
        assert "by_status" in data
        assert data["total"] >= 4

    def test_coverage_requires_kb(self, qa_env):
        client = qa_env["client"]
        response = client.get("/api/qa/coverage")
        assert response.status_code == 422  # Missing required kb param


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
