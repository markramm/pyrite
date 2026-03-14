"""Tests for Cascade JI compatibility audit and backfill migration."""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB

from pyrite_cascade.migration import audit_ji_compat, backfill_ji_fields


@pytest.fixture
def db(tmp_path):
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test", path=kb_path, kb_type="cascade-timeline")],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    db.register_kb("test", "cascade-timeline", str(kb_path))
    yield db
    db.close()


def _old_event(id="old-event", **overrides):
    """Old-style timeline_event without JI fields."""
    data = {
        "id": id,
        "kb_name": "test",
        "title": "Old Event",
        "entry_type": "timeline_event",
        "date": "2020-01-01",
        "metadata": {
            "capture_lanes": ["State Capture"],
            "actors": ["John Doe"],
            "capture_type": "regulatory",
        },
    }
    data.update(overrides)
    return data


def _new_event(id="new-event", **overrides):
    """New-style timeline_event with JI fields."""
    data = {
        "id": id,
        "kb_name": "test",
        "title": "New Event",
        "entry_type": "timeline_event",
        "date": "2020-06-01",
        "metadata": {
            "capture_lanes": ["State Capture"],
            "actors": ["Jane Doe"],
            "source_refs": ["[[source-1]]"],
            "verification_status": "verified",
        },
    }
    data.update(overrides)
    return data


# --- Test: Loading entries with/without JI fields ---


class TestTimelineEventLoadsWithDefaults:
    """Timeline events without JI fields must load with sensible defaults."""

    def test_without_ji_fields_gets_defaults(self):
        from pyrite_cascade.entry_types import TimelineEventEntry

        meta = {
            "id": "old-1",
            "title": "Old Style Event",
            "date": "1996-05-01",
            "actors": ["actor-a"],
            "capture_lanes": ["financial"],
            "capture_type": "privatization",
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "Body text")
        assert entry.source_refs == []
        assert entry.verification_status == "unverified"
        assert entry.actors == ["actor-a"]
        assert entry.capture_lanes == ["financial"]

    def test_with_ji_fields_loads_correctly(self):
        from pyrite_cascade.entry_types import TimelineEventEntry

        meta = {
            "id": "new-1",
            "title": "New Style Event",
            "date": "2020-03-01",
            "actors": ["actor-b"],
            "source_refs": ["[[src-1]]", "[[src-2]]"],
            "verification_status": "verified",
            "capture_lanes": ["political"],
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "Body text")
        assert entry.source_refs == ["[[src-1]]", "[[src-2]]"]
        assert entry.verification_status == "verified"
        assert entry.capture_lanes == ["political"]


# --- Test: audit_ji_compat ---


class TestAuditJiCompat:
    def test_counts_entries_correctly(self, db):
        db.upsert_entry(_old_event(id="old-1"))
        db.upsert_entry(_old_event(id="old-2"))
        db.upsert_entry(_new_event(id="new-1"))

        result = audit_ji_compat(db, "test")
        assert result["total"] == 3
        assert result["with_source_refs"] == 1
        assert result["with_verification_status"] == 1
        assert result["fully_compatible"] == 1
        assert result["needs_backfill"] == 2

    def test_empty_kb_returns_zeros(self, db):
        result = audit_ji_compat(db, "test")
        assert result == {
            "total": 0,
            "with_source_refs": 0,
            "with_verification_status": 0,
            "fully_compatible": 0,
            "needs_backfill": 0,
        }

    def test_all_entries_fully_compatible(self, db):
        db.upsert_entry(_new_event(id="new-1"))
        db.upsert_entry(_new_event(id="new-2"))

        result = audit_ji_compat(db, "test")
        assert result["total"] == 2
        assert result["fully_compatible"] == 2
        assert result["needs_backfill"] == 0

    def test_partial_ji_fields_counted(self, db):
        """Entry with source_refs but no verification_status."""
        db.upsert_entry({
            "id": "partial",
            "kb_name": "test",
            "title": "Partial",
            "entry_type": "timeline_event",
            "date": "2020-01-01",
            "metadata": {
                "source_refs": ["[[src-1]]"],
                "actors": ["Actor A"],
            },
        })
        result = audit_ji_compat(db, "test")
        assert result["total"] == 1
        assert result["with_source_refs"] == 1
        assert result["with_verification_status"] == 0
        assert result["fully_compatible"] == 0
        assert result["needs_backfill"] == 1

    def test_ignores_non_timeline_event_types(self, db):
        """Only timeline_event entries are audited."""
        db.upsert_entry({
            "id": "actor-1",
            "kb_name": "test",
            "title": "An Actor",
            "entry_type": "actor",
            "metadata": {},
        })
        db.upsert_entry(_old_event(id="old-1"))
        result = audit_ji_compat(db, "test")
        assert result["total"] == 1  # only the timeline_event


# --- Test: backfill_ji_fields ---


class TestBackfillJiFields:
    def test_sets_defaults_on_missing_fields(self, db):
        db.upsert_entry(_old_event(id="old-1"))
        result = backfill_ji_fields(db, "test")
        assert result["updated"] == 1
        assert result["skipped"] == 0
        assert result["dry_run"] is False

        entry = db.get_entry("old-1", "test")
        meta = entry["metadata"]
        assert meta["source_refs"] == []
        assert meta["verification_status"] == "unverified"

    def test_dry_run_does_not_modify(self, db):
        db.upsert_entry(_old_event(id="old-1"))
        result = backfill_ji_fields(db, "test", dry_run=True)
        assert result["updated"] == 1
        assert result["dry_run"] is True

        # Entry should NOT have been modified
        entry = db.get_entry("old-1", "test")
        meta = entry["metadata"]
        assert "source_refs" not in meta
        assert "verification_status" not in meta

    def test_skips_already_compatible_entries(self, db):
        db.upsert_entry(_new_event(id="new-1"))
        result = backfill_ji_fields(db, "test")
        assert result["updated"] == 0
        assert result["skipped"] == 1

    def test_cascade_fields_preserved_after_backfill(self, db):
        db.upsert_entry(_old_event(id="old-1"))
        backfill_ji_fields(db, "test")

        entry = db.get_entry("old-1", "test")
        meta = entry["metadata"]
        # Original Cascade fields must be preserved
        assert meta["capture_lanes"] == ["State Capture"]
        assert meta["actors"] == ["John Doe"]
        assert meta["capture_type"] == "regulatory"
        # JI fields added
        assert meta["source_refs"] == []
        assert meta["verification_status"] == "unverified"

    def test_mixed_entries_backfill(self, db):
        db.upsert_entry(_old_event(id="old-1"))
        db.upsert_entry(_old_event(id="old-2"))
        db.upsert_entry(_new_event(id="new-1"))

        result = backfill_ji_fields(db, "test")
        assert result["updated"] == 2
        assert result["skipped"] == 1


# --- Test: Frontmatter round-trip ---


class TestFrontmatterRoundTrip:
    """Loading old Cascade frontmatter samples as a round-trip."""

    def test_old_cascade_event_roundtrip(self):
        from pyrite_cascade.entry_types import TimelineEventEntry

        # Simulate what an old Cascade timeline entry looks like
        meta = {
            "id": "zuma-arms-deal",
            "title": "Zuma Arms Deal Corruption",
            "date": "1999-12-15",
            "importance": 9,
            "actors": ["Jacob Zuma", "Schabir Shaik"],
            "capture_lanes": ["State Capture", "Arms Deal"],
            "capture_type": "procurement",
            "connections": ["arms-deal-overview"],
            "patterns": ["patronage-network"],
            "tags": ["corruption", "arms-deal"],
        }
        entry = TimelineEventEntry.from_frontmatter(meta, "The arms deal...")

        # Verify round-trip
        fm = entry.to_frontmatter()
        entry2 = TimelineEventEntry.from_frontmatter(fm, "The arms deal...")

        assert entry2.id == "zuma-arms-deal"
        assert entry2.date == "1999-12-15"
        assert entry2.actors == ["Jacob Zuma", "Schabir Shaik"]
        assert entry2.capture_lanes == ["State Capture", "Arms Deal"]
        assert entry2.capture_type == "procurement"
        assert entry2.source_refs == []
        assert entry2.verification_status == "unverified"
