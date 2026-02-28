"""
Tests for storage layer (database, repository, index).
"""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.models import EventEntry
from pyrite.models.core_types import PersonEntry
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository


class TestPyriteDB:
    """Tests for PyriteDB."""

    @pytest.fixture
    def db(self):
        """Create a temporary database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PyriteDB(db_path)
            yield db
            db.close()

    def test_create_database(self, db):
        """Test database creation."""
        # Tables should exist
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        assert "kb" in table_names
        assert "entry" in table_names
        assert "tag" in table_names
        assert "link" in table_names

        # Virtual tables are in sqlite_master but not in SQLAlchemy inspector
        row = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entry_fts'"
        ).fetchone()
        assert row is not None

    def test_register_kb(self, db):
        """Test KB registration."""
        db.register_kb("test-kb", "generic", "/tmp/test", "Test KB")

        stats = db.get_kb_stats("test-kb")
        assert stats is not None
        assert stats["name"] == "test-kb"
        assert stats["kb_type"] == "generic"

    def test_upsert_entry(self, db):
        """Test inserting and updating entries."""
        db.register_kb("test-kb", "events", "/tmp/test", "")

        entry_data = {
            "id": "2025-01-20--test-event",
            "kb_name": "test-kb",
            "entry_type": "event",
            "title": "Test Event",
            "body": "This is a test event body.",
            "summary": "Test summary",
            "date": "2025-01-20",
            "importance": 8,
            "tags": ["test", "example"],
            "sources": [{"title": "Source", "url": "https://example.com"}],
            "links": [],
        }

        db.upsert_entry(entry_data)

        # Retrieve
        retrieved = db.get_entry("2025-01-20--test-event", "test-kb")
        assert retrieved is not None
        assert retrieved["title"] == "Test Event"
        assert retrieved["importance"] == 8
        assert len(retrieved["tags"]) == 2

    def test_search_fts(self, db):
        """Test full-text search."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")

        # Insert entries
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Stephen Miller",
                "body": "Stephen Miller is the architect of immigration policy.",
                "summary": "Immigration policy architect",
                "tags": ["immigration"],
            }
        )

        db.upsert_entry(
            {
                "id": "entry-2",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Steve Bannon",
                "body": "Steve Bannon was a White House strategist.",
                "summary": "White House strategist",
                "tags": ["strategy"],
            }
        )

        # Search
        results = db.search("immigration")
        assert len(results) == 1
        assert results[0]["id"] == "entry-1"

        results = db.search("Stephen OR Steve")
        assert len(results) == 2

    def test_search_fts_excludes_body(self, db):
        """FTS search results should not include body to save tokens."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Test Entry",
                "body": "This is a long body that should not appear in search results.",
                "summary": "Short summary",
                "tags": [],
            }
        )

        results = db.search("Test Entry")
        assert len(results) >= 1
        result = results[0]
        assert "body" not in result, "Search results should not include body field"
        # But should still have other useful fields
        assert result["id"] == "entry-1"
        assert result["title"] == "Test Entry"
        assert result["summary"] == "Short summary"
        assert "snippet" in result

    def test_search_by_tag(self, db):
        """Test tag-based search."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")

        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Entry 1",
                "body": "",
                "tags": ["tag-a", "tag-b"],
            }
        )

        db.upsert_entry(
            {
                "id": "entry-2",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Entry 2",
                "body": "",
                "tags": ["tag-b", "tag-c"],
            }
        )

        results = db.search_by_tag("tag-b")
        assert len(results) == 2

        results = db.search_by_tag("tag-a")
        assert len(results) == 1

    def test_links_and_backlinks(self, db):
        """Test link relationships."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")

        db.upsert_entry(
            {
                "id": "source-entry",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Source Entry",
                "body": "",
                "links": [{"target": "target-entry", "relation": "advises", "note": "Test link"}],
            }
        )

        db.upsert_entry(
            {
                "id": "target-entry",
                "kb_name": "test-kb",
                "entry_type": "actor",
                "title": "Target Entry",
                "body": "",
            }
        )

        # Get outgoing links
        outlinks = db.get_outlinks("source-entry", "test-kb")
        assert len(outlinks) == 1
        assert outlinks[0]["relation"] == "advises"

        # Get backlinks
        backlinks = db.get_backlinks("target-entry", "test-kb")
        assert len(backlinks) == 1
        assert backlinks[0]["relation"] == "advised_by"

    def test_timeline_query(self, db):
        """Test timeline queries."""
        db.register_kb("timeline", "events", "/tmp/test", "")

        for i, date in enumerate(["2025-01-10", "2025-01-15", "2025-01-20"]):
            db.upsert_entry(
                {
                    "id": f"{date}--event-{i}",
                    "kb_name": "timeline",
                    "entry_type": "event",
                    "title": f"Event {i}",
                    "body": "",
                    "date": date,
                    "importance": 5 + i,
                }
            )

        results = db.get_timeline(date_from="2025-01-12", date_to="2025-01-18")
        assert len(results) == 1
        assert results[0]["date"] == "2025-01-15"

        results = db.get_timeline(min_importance=6)
        assert len(results) == 2


class TestKBRepository:
    """Tests for KBRepository."""

    @pytest.fixture
    def events_kb(self):
        """Create a temporary events KB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir)
            config = KBConfig(
                name="test-events",
                path=kb_path,
                kb_type="events",
                description="Test events KB",
            )
            yield KBRepository(config)

    @pytest.fixture
    def research_kb(self):
        """Create a temporary research KB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir)
            config = KBConfig(
                name="test-research",
                path=kb_path,
                kb_type="generic",
                description="Test research KB",
            )
            yield KBRepository(config)

    def test_save_and_load_event(self, events_kb):
        """Test saving and loading an event."""
        event = EventEntry.create(
            date="2025-01-20", title="Test Event", body="This is a test event.", importance=8
        )

        path = events_kb.save(event)
        assert path.exists()

        loaded = events_kb.load(event.id)
        assert loaded is not None
        assert loaded.title == "Test Event"
        assert loaded.date == "2025-01-20"

    def test_save_and_load_research(self, research_kb):
        """Test saving and loading a research entry."""
        import re

        entry_id = re.sub(r"[^a-z0-9]+", "-", "John Smith".lower()).strip("-")
        entry = PersonEntry(id=entry_id, title="John Smith", role="test role", importance=6)
        entry.body = "Biography of John Smith."

        path = research_kb.save(entry)
        assert path.exists()
        assert "people" in str(path)  # Should be in people subdirectory

        loaded = research_kb.load(entry.id)
        assert loaded is not None
        assert loaded.title == "John Smith"

    def test_list_entries(self, events_kb):
        """Test listing all entries."""
        # Create some entries
        for i in range(3):
            event = EventEntry.create(date=f"2025-01-{10 + i:02d}", title=f"Event {i}", body="")
            events_kb.save(event)

        entries = list(events_kb.list_entries())
        assert len(entries) == 3

    def test_delete_entry(self, events_kb):
        """Test deleting an entry."""
        event = EventEntry.create(date="2025-01-20", title="To Delete", body="")
        events_kb.save(event)

        assert events_kb.exists(event.id)
        assert events_kb.delete(event.id)
        assert not events_kb.exists(event.id)


class TestIndexManager:
    """Tests for IndexManager."""

    @pytest.fixture
    def setup(self):
        """Create temporary DB and KB for indexing tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create DB
            db_path = tmpdir / "index.db"
            db = PyriteDB(db_path)

            # Create KB directory with some entries
            kb_path = tmpdir / "test-kb"
            kb_path.mkdir()

            kb_config = KBConfig(
                name="test-kb", path=kb_path, kb_type="events", description="Test KB"
            )

            # Create some entries
            repo = KBRepository(kb_config)
            for i in range(5):
                event = EventEntry.create(
                    date=f"2025-01-{10 + i:02d}",
                    title=f"Event {i}",
                    body=f"Body content for event {i}.",
                    importance=5 + i,
                )
                event.tags = ["test", f"tag-{i}"]
                repo.save(event)

            # Create config
            config = PyriteConfig(
                knowledge_bases=[kb_config], settings=Settings(index_path=db_path)
            )

            index_mgr = IndexManager(db, config)

            yield {"db": db, "config": config, "index_mgr": index_mgr, "kb_path": kb_path}

            db.close()

    def test_index_kb(self, setup):
        """Test indexing a KB."""
        count = setup["index_mgr"].index_kb("test-kb")
        assert count == 5

        # Verify in database
        stats = setup["db"].get_kb_stats("test-kb")
        assert stats["entry_count"] == 5

    def test_search_after_index(self, setup):
        """Test searching after indexing."""
        setup["index_mgr"].index_kb("test-kb")

        results = setup["db"].search("Event")
        assert len(results) == 5

        results = setup["db"].search("event 2")
        assert len(results) >= 1

    def test_index_stats(self, setup):
        """Test getting index statistics."""
        setup["index_mgr"].index_kb("test-kb")

        stats = setup["index_mgr"].get_index_stats()
        assert stats["total_entries"] == 5
        assert "test-kb" in stats["kbs"]

    def test_incremental_sync(self, setup):
        """Test incremental sync."""
        # Initial index
        setup["index_mgr"].index_kb("test-kb")

        # Add a new entry
        repo = KBRepository(setup["config"].get_kb("test-kb"))
        new_event = EventEntry.create(date="2025-01-25", title="New Event", body="New event body.")
        repo.save(new_event)

        # Sync
        results = setup["index_mgr"].sync_incremental("test-kb")
        assert results["added"] == 1
        assert results["updated"] == 0
        assert results["removed"] == 0

    def test_check_health_no_false_stale(self, setup):
        """Health check should not report entries as stale immediately after indexing.

        Regression test for timezone mismatch: check_health() compared file mtime
        (local time) with indexed_at (UTC), causing false positives in timezones
        with positive UTC offsets.
        """
        setup["index_mgr"].index_kb("test-kb")

        health = setup["index_mgr"].check_health()
        assert health["stale_entries"] == [], (
            f"Expected no stale entries immediately after indexing, "
            f"got: {health['stale_entries']}"
        )
        assert health["missing_files"] == []
        assert health["unindexed_files"] == []


class TestParseIndexedAt:
    """Tests for _parse_indexed_at() helper in index.py."""

    def test_parse_naive_utc(self):
        """Naive datetime (from SQLite CURRENT_TIMESTAMP) → UTC-aware."""
        from datetime import UTC

        from pyrite.storage.index import _parse_indexed_at

        result = _parse_indexed_at("2026-02-25 12:00:00")
        assert result.tzinfo is not None
        assert result.tzinfo == UTC
        assert result.hour == 12

    def test_parse_with_z_suffix(self):
        """ISO format with Z suffix → UTC-aware."""
        from datetime import UTC

        from pyrite.storage.index import _parse_indexed_at

        result = _parse_indexed_at("2026-02-25T12:00:00Z")
        assert result.tzinfo is not None
        assert result.year == 2026
        assert result.month == 2

    def test_parse_with_offset(self):
        """ISO format with +00:00 offset → UTC-aware."""
        from pyrite.storage.index import _parse_indexed_at

        result = _parse_indexed_at("2026-02-25T12:00:00+00:00")
        assert result.tzinfo is not None
        assert result.hour == 12


class TestIsStaleHelper:
    """Tests for IndexManager._is_stale() helper."""

    def test_stale_file_detected(self, tmp_path):
        """A file newer than indexed_at should be stale."""
        import time

        from pyrite.storage.index import IndexManager

        # indexed_at in the past
        indexed_at = "2020-01-01 00:00:00"
        # Create a file (will have current mtime, much newer)
        f = tmp_path / "test.md"
        f.write_text("hello")
        time.sleep(0.01)  # ensure mtime settles

        assert IndexManager._is_stale(f, indexed_at) is True

    def test_fresh_file_not_stale(self, tmp_path):
        """A file older than indexed_at should not be stale."""
        from pyrite.storage.index import IndexManager

        f = tmp_path / "test.md"
        f.write_text("hello")

        # indexed_at far in the future
        indexed_at = "2099-12-31 23:59:59"
        assert IndexManager._is_stale(f, indexed_at) is False


class TestIntegrationWithExistingKBs:
    """Integration tests with actual CascadeSeries KBs."""

    @pytest.fixture
    def cascade_series_path(self):
        """Path to CascadeSeries if available."""
        path = Path.home() / "CascadeSeries"
        if path.exists():
            return path
        pytest.skip("CascadeSeries not found")

    def test_index_timeline(self, cascade_series_path):
        """Test indexing the actual timeline KB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PyriteDB(db_path)

            timeline_path = cascade_series_path / "timeline" / "hugo-site" / "content" / "events"
            if not timeline_path.exists():
                pytest.skip("Timeline KB not found")

            kb_config = KBConfig(name="timeline", path=timeline_path, kb_type="events")

            config = PyriteConfig(
                knowledge_bases=[kb_config], settings=Settings(index_path=db_path)
            )

            index_mgr = IndexManager(db, config)

            # Index (may take a moment)
            count = index_mgr.index_kb("timeline")
            assert count > 0

            # Search
            results = db.search("Miller")
            assert len(results) > 0

            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
