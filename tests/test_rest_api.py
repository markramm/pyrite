"""
Tests for Pyrite REST API.
"""

import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import EventEntry, PersonEntry
from pyrite.server.api import create_app
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository


@pytest.fixture
def test_env():
    """Create test environment with sample data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"

        events_path = tmpdir / "events"
        events_path.mkdir()

        research_path = tmpdir / "research"
        research_path.mkdir()
        (research_path / "actors").mkdir()

        events_kb = KBConfig(
            name="test-events",
            path=events_path,
            kb_type=KBType.EVENTS,
        )

        research_kb = KBConfig(
            name="test-research",
            path=research_path,
            kb_type=KBType.RESEARCH,
        )

        config = PyriteConfig(
            knowledge_bases=[events_kb, research_kb], settings=Settings(index_path=db_path)
        )

        # Create sample entries
        events_repo = KBRepository(events_kb)
        for i in range(3):
            event = EventEntry.create(
                date=f"2025-01-{10+i:02d}",
                title=f"Test Event {i}",
                body=f"Body for event {i} about immigration policy.",
                importance=5 + i,
            )
            event.tags = ["test", "immigration"]
            event.actors = ["Stephen Miller", "Tom Homan"]
            events_repo.save(event)

        research_repo = KBRepository(research_kb)
        actor = PersonEntry.create(
            name="Stephen Miller", role="Immigration policy architect", importance=9
        )
        actor.body = "Stephen Miller biography."
        actor.tags = ["trump-admin", "immigration"]
        research_repo.save(actor)

        db = PyriteDB(db_path)
        index_mgr = IndexManager(db, config)
        index_mgr.index_all()

        # Inject into app globals
        import pyrite.server.api as api_module

        api_module._config = config
        api_module._db = db
        api_module._index_mgr = index_mgr

        # Create a fresh app for testing (no static files)
        app = create_app(config)
        client = TestClient(app)

        yield {
            "client": client,
            "config": config,
            "db": db,
            "events_kb": events_kb,
            "research_kb": research_kb,
        }

        db.close()

        # Reset globals
        api_module._config = None
        api_module._db = None
        api_module._index_mgr = None


class TestKBEndpoints:
    """Test KB listing endpoint."""

    def test_list_kbs(self, test_env):
        client = test_env["client"]
        response = client.get("/api/kbs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["kbs"]) == 2

    def test_health_check(self, test_env):
        client = test_env["client"]
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestSearchEndpoints:
    """Test search functionality."""

    def test_basic_search(self, test_env):
        client = test_env["client"]
        response = client.get("/api/search?q=immigration")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "immigration"
        assert data["count"] >= 1

    def test_search_with_kb_filter(self, test_env):
        client = test_env["client"]
        response = client.get("/api/search?q=Test&kb=test-events")
        assert response.status_code == 200
        data = response.json()
        # Should only return events
        for result in data["results"]:
            assert result["kb_name"] == "test-events"

    def test_search_with_limit(self, test_env):
        client = test_env["client"]
        response = client.get("/api/search?q=Test&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 2


class TestEntryEndpoints:
    """Test entry CRUD operations."""

    def test_get_entry_not_found(self, test_env):
        client = test_env["client"]
        response = client.get("/api/entries/nonexistent-entry")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    def test_get_entry(self, test_env):
        client = test_env["client"]
        # First search to find an entry
        search_response = client.get("/api/search?q=Stephen+Miller&kb=test-research")
        if search_response.json()["count"] > 0:
            entry_id = search_response.json()["results"][0]["id"]
            response = client.get(f"/api/entries/{entry_id}?kb=test-research")
            assert response.status_code == 200
            data = response.json()
            assert "title" in data
            assert "body" in data

    def test_list_entries(self, test_env):
        client = test_env["client"]
        response = client.get("/api/entries?kb=test-events&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["entries"]) <= 10

    def test_create_entry_json(self, test_env):
        client = test_env["client"]
        response = client.post(
            "/api/entries",
            json={
                "kb": "test-events",
                "entry_type": "event",
                "title": "New API Event",
                "body": "Created via JSON body",
                "date": "2025-06-01",
                "tags": ["api-test"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True
        assert "id" in data

    def test_update_entry_json(self, test_env):
        client = test_env["client"]
        # Create then update
        create_resp = client.post(
            "/api/entries",
            json={
                "kb": "test-events",
                "entry_type": "event",
                "title": "Update Test Event",
                "body": "Original body",
                "date": "2025-07-01",
            },
        )
        entry_id = create_resp.json()["id"]
        response = client.put(
            f"/api/entries/{entry_id}",
            json={"kb": "test-events", "body": "Updated body"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] is True


class TestTimelineEndpoints:
    """Test timeline queries."""

    def test_timeline_basic(self, test_env):
        client = test_env["client"]
        response = client.get("/api/timeline?date_from=2025-01-01&date_to=2025-12-31")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data

    def test_timeline_with_limit(self, test_env):
        client = test_env["client"]
        response = client.get("/api/timeline?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) <= 2


class TestTagsAndActors:
    """Test tags and actors endpoints."""

    def test_get_tags(self, test_env):
        client = test_env["client"]
        response = client.get("/api/tags")
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        assert "count" in data


class TestAdminEndpoints:
    """Test admin endpoints."""

    def test_get_stats(self, test_env):
        client = test_env["client"]
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
