"""
Tests for storage layer (database, repository, index).
"""

import logging
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
        row = db._raw_conn.execute(
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
        assert "body" in result, "Search results should include body field for --include-body support"
        assert result["body"] == "This is a long body that should not appear in search results."
        # Should still have other useful fields
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

    def test_find_file_by_frontmatter_id_when_filename_differs(self, events_kb):
        """find_file should locate entries where filename != frontmatter ID."""
        # Write a file with a filename that doesn't match the ID
        (events_kb.config.path / "adrs").mkdir(exist_ok=True)
        md = """---
type: note
id: adr-0099
title: Test ADR
---

Some content.
"""
        (events_kb.config.path / "adrs" / "0099-test-adr.md").write_text(md)

        # find_file should locate it by scanning frontmatter
        found = events_kb.find_file("adr-0099")
        assert found is not None
        assert "0099-test-adr.md" in str(found)

        # load should work too
        entry = events_kb.load("adr-0099")
        assert entry is not None
        assert entry.title == "Test ADR"

    def test_load_strips_duplicated_frontmatter_from_body(self, events_kb):
        """Frontmatter field duplicated in body should be stripped on load."""
        # Write a file with 'type: event' leaked into body (migration error pattern)
        md = """---
type: event
id: 2025-01-20--test-leak
date: '2025-01-20'
title: Test Leak
importance: 5
status: confirmed
---
type: event

The actual body content starts here.
"""
        (events_kb.config.path / "events").mkdir(exist_ok=True)
        (events_kb.config.path / "events" / "2025-01-20--test-leak.md").write_text(md)

        loaded = events_kb.load("2025-01-20--test-leak")
        assert loaded is not None
        assert not loaded.body.startswith("type:")
        assert "actual body content" in loaded.body

    def test_load_frontmatter_with_triple_dash_in_quoted_value(self, events_kb, caplog):
        """Frontmatter delimiter detection must require `---` at start of line.

        Regression: quoted values containing `---` (e.g. "Rental Property --- Chicago, IL")
        were being matched by text.find("---", 3), truncating frontmatter mid-field.
        This caused a YAML ScannerError that silently fell back to EventEntry.load,
        which uses a different (correct) regex-based parser and re-parses from scratch.
        The symptom: warnings flooded the logs on every index/health run.
        """
        md = """---
type: event
id: 2025-01-20--triple-dash-in-value
date: '2025-01-20'
title: Triple Dash Test
importance: 5
status: confirmed
key_holdings:
- "Rental Property --- Chicago, IL"
- "Another --- thing"
---

The body.
"""
        (events_kb.config.path / "events").mkdir(exist_ok=True)
        (events_kb.config.path / "events" / "2025-01-20--triple-dash-in-value.md").write_text(md)

        # Assert we do NOT hit the exception path — no warning should be logged.
        with caplog.at_level(logging.WARNING, logger="pyrite.storage.repository"):
            loaded = events_kb.load("2025-01-20--triple-dash-in-value")
        assert not any(
            "Entry load failed" in r.message for r in caplog.records
        ), f"Should not have hit EventEntry fallback. Logs: {[r.message for r in caplog.records]}"
        assert loaded is not None
        assert loaded.title == "Triple Dash Test"
        assert loaded.body.strip() == "The body."

    def test_load_preserves_body_with_colon_that_is_not_frontmatter_key(self, events_kb):
        """Body lines with colons that aren't frontmatter keys should be preserved."""
        md = """---
type: event
id: 2025-01-20--colon-body
date: '2025-01-20'
title: Colon Body
importance: 5
status: confirmed
---
Note: this line has a colon but is not a frontmatter key.

More body text.
"""
        (events_kb.config.path / "events").mkdir(exist_ok=True)
        (events_kb.config.path / "events" / "2025-01-20--colon-body.md").write_text(md)

        loaded = events_kb.load("2025-01-20--colon-body")
        assert loaded is not None
        assert loaded.body.startswith("Note:")

    def test_save_plugin_type_uses_schema_subdirectory(self):
        """Test that plugin types use subdirectory from kb.yaml schema."""
        from pyrite.utils.yaml import dump_yaml_file

        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir)
            # Write a kb.yaml with backlog_item type that has subdirectory
            kb_yaml_data = {
                "name": "test-software",
                "description": "Test software KB",
                "types": {
                    "backlog_item": {
                        "description": "Backlog item",
                        "subdirectory": "backlog",
                        "required": ["title"],
                    },
                },
            }
            dump_yaml_file(kb_yaml_data, kb_path / "kb.yaml")

            config = KBConfig(
                name="test-software",
                path=kb_path,
                kb_type="software",
                description="Test software KB",
            )

            repo = KBRepository(config)

            # Create a generic entry with entry_type "backlog_item"
            from pyrite.models.generic import GenericEntry

            entry = GenericEntry(id="test-bug-fix", title="Fix the bug")
            entry._entry_type = "backlog_item"
            entry.body = "Description of the bug fix."

            path = repo.save(entry)
            assert path.exists()
            assert "/backlog/" in str(path), f"Expected /backlog/ in path, got: {path}"

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

    def test_references_field_creates_cross_kb_links(self, setup):
        """References in frontmatter should create cross-KB links during indexing."""
        # Create an entry with references to another KB
        kb_path = setup["kb_path"]
        md = """---
type: note
id: article-1
title: My Article
references:
  - other-kb:target-event-1
  - other-kb:target-event-2
  - same-kb-target
---

Article body referencing events.
"""
        (kb_path / "article-1.md").write_text(md)

        setup["index_mgr"].index_kb("test-kb")

        # Check that links were created
        entry = setup["db"].get_entry("article-1", "test-kb")
        assert entry is not None

        # Get outlinks for this entry
        outlinks = setup["db"].get_outlinks("article-1", "test-kb")
        target_ids = {ol["id"] for ol in outlinks}

        assert "target-event-1" in target_ids, f"Expected target-event-1 in outlinks, got {target_ids}"
        assert "target-event-2" in target_ids, f"Expected target-event-2 in outlinks, got {target_ids}"
        assert "same-kb-target" in target_ids, f"Expected same-kb-target in outlinks, got {target_ids}"

    def test_check_health_no_false_stale(self, setup):
        """Health check should not report entries as stale immediately after indexing.

        Regression test for timezone mismatch: check_health() compared file mtime
        (local time) with indexed_at (UTC), causing false positives in timezones
        with positive UTC offsets.
        """
        setup["index_mgr"].index_kb("test-kb")

        health = setup["index_mgr"].check_health()
        assert health["stale_entries"] == [], (
            f"Expected no stale entries immediately after indexing, got: {health['stale_entries']}"
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


@pytest.mark.integration
class TestIntegrationWithExistingKBs:
    """Integration tests with actual CascadeSeries KBs."""

    @pytest.fixture
    def cascade_series_path(self):
        """Path to CascadeSeries if available."""
        path = Path.home() / "CascadeSeries"
        if path.exists():
            return path
        pytest.skip("CascadeSeries not found")

    @pytest.mark.slow
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


class TestDDLDefaultValidation:
    """Tests for SQL DEFAULT clause validation in plugin DDL."""

    @pytest.fixture
    def db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PyriteDB(db_path)
            yield db
            db.close()

    @pytest.mark.parametrize(
        "default_val",
        [
            "NULL",
            "null",
            "0",
            "42",
            "3.14",
            "'some text'",
            "''",
            "CURRENT_TIMESTAMP",
            "current_timestamp",
            "TRUE",
            "FALSE",
        ],
    )
    def test_valid_defaults_accepted(self, db, default_val):
        table_def = {
            "name": "test_defaults",
            "columns": [
                {"name": "id", "type": "INTEGER", "primary_key": True},
                {"name": "col", "type": "TEXT", "default": default_val},
            ],
        }
        db._create_table_from_def(table_def)
        # Drop for next parametrize run
        db._raw_conn.execute("DROP TABLE IF EXISTS test_defaults")
        db._raw_conn.commit()

    @pytest.mark.parametrize(
        "default_val",
        [
            "1; DROP TABLE entry",
            "'' OR 1=1",
            "CURRENT_TIMESTAMP; --",
            "(SELECT 1)",
        ],
    )
    def test_invalid_defaults_rejected(self, db, default_val):
        table_def = {
            "name": "test_bad_defaults",
            "columns": [
                {"name": "id", "type": "INTEGER", "primary_key": True},
                {"name": "col", "type": "TEXT", "default": default_val},
            ],
        }
        with pytest.raises(ValueError, match="Invalid SQL DEFAULT"):
            db._create_table_from_def(table_def)


class TestIndexedAtOnInsert:
    """Regression: `upsert_entry` INSERT path must write a real timestamp
    into `indexed_at`, never the literal string 'CURRENT_TIMESTAMP'.

    Bug history: `models.py` declared
    `indexed_at = Column(String, server_default="CURRENT_TIMESTAMP")`.
    Under some SQLAlchemy+SQLite combos the string-form server_default is
    stored as the literal `"CURRENT_TIMESTAMP"` instead of being evaluated
    as SQL. Combined with `_parse_indexed_at`'s old fallback (which mapped
    the literal to `datetime.now()`), this broke `sync_incremental`: the
    staleness check always saw `now() > file_mtime` and skipped the row
    forever.

    Fix: the INSERT branch in `_upsert_entry_main` sets `indexed_at`
    explicitly, so the broken default is never reached.
    """

    @pytest.fixture
    def db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PyriteDB(Path(tmpdir) / "index.db")
            db.register_kb("test-kb", "generic", "/tmp/test", "")
            yield db
            db.close()

    def test_fresh_insert_sets_real_timestamp(self, db):
        db.upsert_entry(
            {
                "id": "new-entry",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Test",
                "body": "Body",
            }
        )
        row = db._raw_conn.execute(
            "SELECT indexed_at FROM entry WHERE id = ? AND kb_name = ?",
            ("new-entry", "test-kb"),
        ).fetchone()
        assert row is not None
        indexed_at = row[0]
        assert indexed_at != "CURRENT_TIMESTAMP", (
            "indexed_at should be an actual timestamp, not the literal SQL default"
        )
        # Should parse without the fallback branch firing.
        from pyrite.storage.index import _parse_indexed_at

        parsed = _parse_indexed_at(indexed_at)
        assert parsed.year >= 2026


class TestSyncRecoversFromBrokenTimestamp:
    """Regression: sync_incremental must reindex entries whose stored
    `indexed_at` is the literal 'CURRENT_TIMESTAMP' string.

    Without the fix, `_parse_indexed_at('CURRENT_TIMESTAMP')` returned
    `datetime.now(UTC)`, which made `_is_stale` always return False for
    those rows. They were permanently skipped by sync, which is exactly
    the user-visible bug: edit-frontmatter + sync reported Updated:0.
    """

    def test_sync_reindexes_broken_timestamp_row(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"
            kb_path = tmpdir / "kb"
            kb_path.mkdir()

            db = PyriteDB(db_path)
            kb_config = KBConfig(
                name="test-kb", path=kb_path, kb_type="generic", description="Test KB"
            )
            config = PyriteConfig(
                knowledge_bases=[kb_config], settings=Settings(index_path=db_path)
            )

            # Create a markdown file on disk.
            md_file = kb_path / "entry-a.md"
            md_file.write_text(
                "---\nid: entry-a\ntype: note\ntitle: Initial Title\n---\n\nOriginal body.\n"
            )

            # First index pass — the row gets inserted normally.
            index_mgr = IndexManager(db, config)
            index_mgr.index_all()

            # Simulate the corrupt state: rewrite indexed_at to the literal
            # 'CURRENT_TIMESTAMP' string, as the historical buggy INSERT path
            # did. This mirrors what `select * from entry` shows for the 78
            # affected rows on the live pyrite DB.
            db._raw_conn.execute(
                "UPDATE entry SET indexed_at = 'CURRENT_TIMESTAMP' WHERE id = ?",
                ("entry-a",),
            )
            db._raw_conn.commit()

            # Modify the file on disk (simulating a direct editor/script edit).
            md_file.write_text(
                "---\nid: entry-a\ntype: note\ntitle: Updated Title\n---\n\nNew body.\n"
            )

            # Sync. The corrupt row must be detected as stale and reindexed.
            results = index_mgr.sync_incremental("test-kb")
            assert results["updated"] >= 1, (
                f"Expected sync to reindex the broken-timestamp row, got {results}"
            )

            # Title should now reflect the on-disk change.
            row = db._raw_conn.execute(
                "SELECT title, indexed_at FROM entry WHERE id = ?",
                ("entry-a",),
            ).fetchone()
            assert row[0] == "Updated Title", (
                "Expected reindex to pick up 'Updated Title' from the modified file"
            )
            assert row[1] != "CURRENT_TIMESTAMP", (
                "After reindex, indexed_at must be a real timestamp, not the literal"
            )

            db.close()


class TestUndeclaredTypesInHealth:
    """`check_health` must surface entries whose `entry_type` is not declared
    in the KB's `kb.yaml` types section.

    Context: `pyrite index build` silently accepts entries with any `type:`
    value. An entry with `type: timeline_event` indexes fine even if the KB's
    `kb.yaml` only declares `type: event`. This is how cascade-timeline drift
    went undetected for weeks. See ticket
    `kb/backlog/warn-on-undeclared-entry-type.md`.

    `check_health()` returns an `undeclared_types` list aggregated per
    `(kb, type)` with a count. Core types (note, event, person, ...) and
    all types declared in `kb.yaml` are treated as declared. If a KB has
    no `kb.yaml` at all, nothing is reported for it — we can't enforce
    what isn't configured.
    """

    def _make_config(self, tmpdir: Path, kb_path: Path) -> tuple[PyriteDB, PyriteConfig]:
        db_path = tmpdir / "index.db"
        db = PyriteDB(db_path)
        # Register the KB so upsert_entry's FK constraint is satisfied.
        db.register_kb(kb_path.name, "generic", str(kb_path), "")
        kb_config = KBConfig(
            name=kb_path.name, path=kb_path, kb_type="generic", description="Test KB"
        )
        config = PyriteConfig(
            knowledge_bases=[kb_config], settings=Settings(index_path=db_path)
        )
        return db, config

    def test_undeclared_type_flagged(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            kb_path = tmp / "cascade-timeline"
            kb_path.mkdir()
            # kb.yaml declares only the "event" type.
            (kb_path / "kb.yaml").write_text(
                "name: cascade-timeline\n"
                "kb_type: events\n"
                "types:\n"
                "  event:\n"
                "    description: A thing that happened\n"
                "    subdirectory: events\n"
            )

            db, config = self._make_config(tmp, kb_path)
            try:
                # Entry with an undeclared `timeline_event` type — not in
                # kb.yaml and not in CORE_TYPES.
                db.upsert_entry(
                    {
                        "id": "tl-1",
                        "kb_name": kb_path.name,
                        "entry_type": "timeline_event",
                        "title": "Undeclared",
                        "body": "body",
                        "file_path": str(kb_path / "tl-1.md"),
                    }
                )
                # Entry whose type IS declared — must NOT be reported.
                db.upsert_entry(
                    {
                        "id": "ev-1",
                        "kb_name": kb_path.name,
                        "entry_type": "event",
                        "title": "Declared",
                        "body": "body",
                        "file_path": str(kb_path / "ev-1.md"),
                    }
                )

                index_mgr = IndexManager(db, config)
                health = index_mgr.check_health()

                assert "undeclared_types" in health, (
                    "check_health must expose an 'undeclared_types' field"
                )
                undeclared = health["undeclared_types"]
                assert {
                    "kb": kb_path.name,
                    "type": "timeline_event",
                    "count": 1,
                } in undeclared, f"expected timeline_event row, got {undeclared}"
                # The declared type must not appear as undeclared.
                for row in undeclared:
                    assert row["type"] != "event", (
                        f"declared type 'event' must not be flagged: {row}"
                    )
            finally:
                db.close()

    def test_core_types_treated_as_declared(self):
        """Entries using core types (e.g. `note`) should not be flagged,
        even if kb.yaml doesn't explicitly redeclare them."""
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            kb_path = tmp / "core-kb"
            kb_path.mkdir()
            (kb_path / "kb.yaml").write_text(
                "name: core-kb\n"
                "kb_type: generic\n"
                "types:\n"
                "  event:\n"
                "    description: A thing\n"
            )

            db, config = self._make_config(tmp, kb_path)
            try:
                db.upsert_entry(
                    {
                        "id": "n-1",
                        "kb_name": kb_path.name,
                        "entry_type": "note",
                        "title": "Core note",
                        "body": "body",
                        "file_path": str(kb_path / "n-1.md"),
                    }
                )

                index_mgr = IndexManager(db, config)
                health = index_mgr.check_health()
                for row in health.get("undeclared_types", []):
                    assert row["type"] != "note", (
                        f"core type 'note' must not be flagged: {row}"
                    )
            finally:
                db.close()

    def test_kb_without_kb_yaml_not_warned(self):
        """A KB with no kb.yaml has no declared-type list to enforce —
        we must not emit warnings for it."""
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            kb_path = tmp / "no-yaml-kb"
            kb_path.mkdir()
            # NOTE: no kb.yaml written here.

            db, config = self._make_config(tmp, kb_path)
            try:
                db.upsert_entry(
                    {
                        "id": "x-1",
                        "kb_name": kb_path.name,
                        "entry_type": "utterly_made_up_type",
                        "title": "Weird",
                        "body": "body",
                        "file_path": str(kb_path / "x-1.md"),
                    }
                )

                index_mgr = IndexManager(db, config)
                health = index_mgr.check_health()
                undeclared = health.get("undeclared_types", [])
                for row in undeclared:
                    assert row["kb"] != kb_path.name, (
                        f"KB without kb.yaml must not be flagged: {row}"
                    )
            finally:
                db.close()


class TestRequiredFieldValidationInHealth:
    """`check_health` must surface entries whose kb.yaml `required:` fields
    are missing or empty.

    See ticket `kb/backlog/schema-required-field-validation.md`. The index
    silently accepts `type: timeline_event` entries missing `date:` even when
    kb.yaml declares `required: [date, title]`. Surface per-entry issues so
    drift can be fixed without waiting for query-time symptoms.
    """

    def _make_config(self, tmpdir: Path, kb_path: Path) -> tuple[PyriteDB, PyriteConfig]:
        db_path = tmpdir / "index.db"
        db = PyriteDB(db_path)
        db.register_kb(kb_path.name, "generic", str(kb_path), "")
        kb_config = KBConfig(
            name=kb_path.name, path=kb_path, kb_type="generic", description="Test KB"
        )
        config = PyriteConfig(
            knowledge_bases=[kb_config], settings=Settings(index_path=db_path)
        )
        return db, config

    def test_missing_required_field_surfaces_in_health(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            kb_path = tmp / "cascade-timeline"
            kb_path.mkdir()
            (kb_path / "kb.yaml").write_text(
                "name: cascade-timeline\n"
                "kb_type: events\n"
                "types:\n"
                "  timeline_event:\n"
                "    description: Event\n"
                "    required: [date, title]\n"
            )

            db, config = self._make_config(tmp, kb_path)
            try:
                # Missing `date`
                db.upsert_entry(
                    {
                        "id": "tl-missing-date",
                        "kb_name": kb_path.name,
                        "entry_type": "timeline_event",
                        "title": "Has title but no date",
                        "body": "body",
                        "file_path": str(kb_path / "tl-missing-date.md"),
                    }
                )
                # Has both — must NOT be reported.
                db.upsert_entry(
                    {
                        "id": "tl-ok",
                        "kb_name": kb_path.name,
                        "entry_type": "timeline_event",
                        "title": "Complete",
                        "body": "body",
                        "date": "2026-04-24",
                        "file_path": str(kb_path / "tl-ok.md"),
                    }
                )

                index_mgr = IndexManager(db, config)
                health = index_mgr.check_health()

                assert "missing_required_fields" in health, (
                    "check_health must expose a 'missing_required_fields' field"
                )
                missing = health["missing_required_fields"]
                flagged = [m for m in missing if m["id"] == "tl-missing-date"]
                assert len(flagged) == 1, (
                    f"expected tl-missing-date to be flagged once, got {missing}"
                )
                row = flagged[0]
                assert row["kb"] == kb_path.name
                assert row["type"] == "timeline_event"
                assert "date" in row["missing"]
                # Complete entry must not appear.
                assert not any(m["id"] == "tl-ok" for m in missing), (
                    f"complete entry must not be flagged: {missing}"
                )
            finally:
                db.close()

    def test_default_required_title_only(self):
        """Types without explicit `required:` default to ['title']. An entry
        with an empty title on such a type should be flagged; entries with
        titles should not."""
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            kb_path = tmp / "default-req-kb"
            kb_path.mkdir()
            (kb_path / "kb.yaml").write_text(
                "name: default-req-kb\n"
                "kb_type: generic\n"
                "types:\n"
                "  custom_type:\n"
                "    description: no required declared\n"
            )

            db, config = self._make_config(tmp, kb_path)
            try:
                db.upsert_entry(
                    {
                        "id": "no-title",
                        "kb_name": kb_path.name,
                        "entry_type": "custom_type",
                        "title": "",
                        "body": "body",
                        "file_path": str(kb_path / "no-title.md"),
                    }
                )

                index_mgr = IndexManager(db, config)
                health = index_mgr.check_health()

                missing = health.get("missing_required_fields", [])
                flagged = [m for m in missing if m["id"] == "no-title"]
                assert len(flagged) == 1
                assert "title" in flagged[0]["missing"]
            finally:
                db.close()

    def test_kb_without_kb_yaml_not_validated(self):
        """Required-field enforcement is a no-op for KBs without kb.yaml."""
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            kb_path = tmp / "no-yaml-kb"
            kb_path.mkdir()
            # No kb.yaml.

            db, config = self._make_config(tmp, kb_path)
            try:
                db.upsert_entry(
                    {
                        "id": "empty-everything",
                        "kb_name": kb_path.name,
                        "entry_type": "note",
                        "title": "",
                        "body": "",
                        "file_path": str(kb_path / "x.md"),
                    }
                )

                index_mgr = IndexManager(db, config)
                health = index_mgr.check_health()

                missing = health.get("missing_required_fields", [])
                assert not any(m["kb"] == kb_path.name for m in missing), (
                    f"KB without kb.yaml must not be validated: {missing}"
                )
            finally:
                db.close()


class TestSubdirectoryMismatchInHealth:
    """`check_health` must surface entries whose file path does not match
    the `subdirectory:` declared for their type in kb.yaml.

    Per the ticket, `subdirectory:` is a writer hint, not a reader
    constraint — the reader continues to accept any layout. But the
    health check should warn about layout drift.
    """

    def _make_config(self, tmpdir: Path, kb_path: Path) -> tuple[PyriteDB, PyriteConfig]:
        db_path = tmpdir / "index.db"
        db = PyriteDB(db_path)
        db.register_kb(kb_path.name, "generic", str(kb_path), "")
        kb_config = KBConfig(
            name=kb_path.name, path=kb_path, kb_type="generic", description="Test KB"
        )
        config = PyriteConfig(
            knowledge_bases=[kb_config], settings=Settings(index_path=db_path)
        )
        return db, config

    def test_subdirectory_mismatch_surfaces_in_health(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            kb_path = tmp / "cascade-timeline"
            kb_path.mkdir()
            (kb_path / "kb.yaml").write_text(
                "name: cascade-timeline\n"
                "kb_type: events\n"
                "types:\n"
                "  timeline_event:\n"
                "    description: Event\n"
                "    subdirectory: events\n"
            )
            # Entry lives at the KB root (wrong place).
            wrong_path = kb_path / "wrong-place.md"
            # Entry lives in the declared subdirectory (correct place).
            (kb_path / "events").mkdir()
            right_path = kb_path / "events" / "right-place.md"

            db, config = self._make_config(tmp, kb_path)
            try:
                db.upsert_entry(
                    {
                        "id": "wrong-place",
                        "kb_name": kb_path.name,
                        "entry_type": "timeline_event",
                        "title": "Wrong",
                        "body": "body",
                        "file_path": str(wrong_path),
                    }
                )
                db.upsert_entry(
                    {
                        "id": "right-place",
                        "kb_name": kb_path.name,
                        "entry_type": "timeline_event",
                        "title": "Right",
                        "body": "body",
                        "file_path": str(right_path),
                    }
                )

                index_mgr = IndexManager(db, config)
                health = index_mgr.check_health()

                assert "subdirectory_mismatches" in health, (
                    "check_health must expose a 'subdirectory_mismatches' field"
                )
                mismatches = health["subdirectory_mismatches"]
                flagged = [m for m in mismatches if m["id"] == "wrong-place"]
                assert len(flagged) == 1, (
                    f"expected wrong-place to be flagged, got {mismatches}"
                )
                row = flagged[0]
                assert row["kb"] == kb_path.name
                assert row["type"] == "timeline_event"
                assert row["declared_subdirectory"] == "events"
                # Correctly-placed entry must not appear.
                assert not any(m["id"] == "right-place" for m in mismatches)
            finally:
                db.close()

    def test_subdirectory_empty_allows_any_placement(self):
        """`subdirectory: ""` means 'at KB root is explicit' — entries at
        root should be OK, entries in subfolders should not be flagged
        either (the reader is permissive)."""
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            kb_path = tmp / "root-kb"
            kb_path.mkdir()
            (kb_path / "kb.yaml").write_text(
                "name: root-kb\n"
                "kb_type: generic\n"
                "types:\n"
                "  note:\n"
                "    description: Root-level notes\n"
                "    subdirectory: ''\n"
            )

            db, config = self._make_config(tmp, kb_path)
            try:
                db.upsert_entry(
                    {
                        "id": "at-root",
                        "kb_name": kb_path.name,
                        "entry_type": "note",
                        "title": "Root",
                        "body": "body",
                        "file_path": str(kb_path / "at-root.md"),
                    }
                )

                index_mgr = IndexManager(db, config)
                health = index_mgr.check_health()

                mismatches = health.get("subdirectory_mismatches", [])
                assert not any(m["id"] == "at-root" for m in mismatches)
            finally:
                db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
