"""
Tests for starred/pinned entries feature (backlog item #9).
"""

import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import EventEntry
from pyrite.server.api import app
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository


@pytest.fixture
def starred_env():
    """Create test environment for starred entries tests."""
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
            knowledge_bases=[events_kb],
            settings=Settings(index_path=db_path),
        )

        # Create sample entries
        events_repo = KBRepository(events_kb)
        for i in range(3):
            event = EventEntry.create(
                date=f"2025-01-{10+i:02d}",
                title=f"Test Event {i}",
                body=f"Body for event {i}.",
                importance=5,
            )
            event.tags = ["test"]
            events_repo.save(event)

        db = PyriteDB(db_path)
        index_mgr = IndexManager(db, config)
        index_mgr.index_all()

        # Inject into app globals
        import pyrite.server.api as api_module

        api_module._config = config
        api_module._db = db
        api_module._index_mgr = index_mgr

        client = TestClient(app)

        yield {
            "client": client,
            "config": config,
            "db": db,
        }

        db.close()

        # Reset globals
        api_module._config = None
        api_module._db = None
        api_module._index_mgr = None


class TestStarEntry:
    """Test starring an entry."""

    def test_star_entry(self, starred_env):
        client = starred_env["client"]
        response = client.post(
            "/api/starred",
            json={"entry_id": "test-event-0", "kb_name": "test-events"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["starred"] is True
        assert data["entry_id"] == "test-event-0"
        assert data["kb_name"] == "test-events"

    def test_star_duplicate_is_idempotent(self, starred_env):
        client = starred_env["client"]
        # Star once
        client.post(
            "/api/starred",
            json={"entry_id": "test-event-0", "kb_name": "test-events"},
        )
        # Star again — should succeed (idempotent)
        response = client.post(
            "/api/starred",
            json={"entry_id": "test-event-0", "kb_name": "test-events"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["starred"] is True

    def test_star_nonexistent_entry(self, starred_env):
        """Starring a non-existent entry_id is allowed (engagement-tier, no FK to entries)."""
        client = starred_env["client"]
        response = client.post(
            "/api/starred",
            json={"entry_id": "does-not-exist", "kb_name": "test-events"},
        )
        # Engagement data doesn't enforce FK to content entries
        assert response.status_code == 200
        data = response.json()
        assert data["starred"] is True


class TestUnstarEntry:
    """Test unstarring an entry."""

    def test_unstar_entry(self, starred_env):
        client = starred_env["client"]
        # Star first
        client.post(
            "/api/starred",
            json={"entry_id": "test-event-0", "kb_name": "test-events"},
        )
        # Unstar
        response = client.delete("/api/starred/test-event-0?kb=test-events")
        assert response.status_code == 200
        data = response.json()
        assert data["unstarred"] is True
        assert data["entry_id"] == "test-event-0"

    def test_unstar_nonexistent(self, starred_env):
        client = starred_env["client"]
        response = client.delete("/api/starred/nonexistent?kb=test-events")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"


class TestListStarred:
    """Test listing starred entries."""

    def test_list_empty(self, starred_env):
        client = starred_env["client"]
        response = client.get("/api/starred")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["starred"] == []

    def test_list_starred_entries(self, starred_env):
        client = starred_env["client"]
        # Star two entries
        client.post(
            "/api/starred",
            json={"entry_id": "test-event-0", "kb_name": "test-events"},
        )
        client.post(
            "/api/starred",
            json={"entry_id": "test-event-1", "kb_name": "test-events"},
        )

        response = client.get("/api/starred")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["starred"]) == 2

    def test_list_starred_filter_by_kb(self, starred_env):
        client = starred_env["client"]
        client.post(
            "/api/starred",
            json={"entry_id": "test-event-0", "kb_name": "test-events"},
        )
        client.post(
            "/api/starred",
            json={"entry_id": "other-entry", "kb_name": "other-kb"},
        )

        # Filter by kb
        response = client.get("/api/starred?kb=test-events")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["starred"][0]["kb_name"] == "test-events"

    def test_starred_entries_have_sort_order(self, starred_env):
        client = starred_env["client"]
        client.post(
            "/api/starred",
            json={"entry_id": "test-event-0", "kb_name": "test-events"},
        )
        client.post(
            "/api/starred",
            json={"entry_id": "test-event-1", "kb_name": "test-events"},
        )

        response = client.get("/api/starred")
        data = response.json()
        # sort_order should be sequential
        orders = [s["sort_order"] for s in data["starred"]]
        assert orders == sorted(orders)


class TestReorderStarred:
    """Test reordering starred entries."""

    def test_reorder(self, starred_env):
        client = starred_env["client"]
        # Star entries
        client.post(
            "/api/starred",
            json={"entry_id": "test-event-0", "kb_name": "test-events"},
        )
        client.post(
            "/api/starred",
            json={"entry_id": "test-event-1", "kb_name": "test-events"},
        )

        # Reorder: swap positions
        response = client.put(
            "/api/starred/reorder",
            json={
                "entries": [
                    {"entry_id": "test-event-0", "kb_name": "test-events", "sort_order": 2},
                    {"entry_id": "test-event-1", "kb_name": "test-events", "sort_order": 1},
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["reordered"] is True
        assert data["count"] == 2

        # Verify order
        list_response = client.get("/api/starred")
        starred = list_response.json()["starred"]
        assert starred[0]["entry_id"] == "test-event-1"
        assert starred[1]["entry_id"] == "test-event-0"

    def test_reorder_empty(self, starred_env):
        client = starred_env["client"]
        response = client.put(
            "/api/starred/reorder",
            json={"entries": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["reordered"] is True
        assert data["count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
