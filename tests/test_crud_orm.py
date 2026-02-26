"""Tests for ORM-based CRUD operations matching previous raw SQL behavior."""

import tempfile
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB


@pytest.fixture
def db():
    """Fresh PyriteDB with a registered KB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = PyriteDB(Path(tmpdir) / "test.db")
        db.register_kb("test", "generic", "/tmp/test")
        yield db
        db.close()


def _make_entry(entry_id="e1", **overrides):
    """Helper to build entry data dict."""
    data = {
        "id": entry_id,
        "kb_name": "test",
        "entry_type": "note",
        "title": f"Title {entry_id}",
        "body": f"Body for {entry_id}",
        "tags": [],
        "sources": [],
        "links": [],
    }
    data.update(overrides)
    return data


class TestUpsertEntry:
    """Test upsert_entry ORM implementation."""

    def test_insert_new_entry(self, db):
        db.upsert_entry(_make_entry("new1", title="New Entry"))
        entry = db.get_entry("new1", "test")
        assert entry is not None
        assert entry["title"] == "New Entry"
        assert entry["entry_type"] == "note"

    def test_update_existing_entry(self, db):
        db.upsert_entry(_make_entry("up1", title="V1"))
        db.upsert_entry(_make_entry("up1", title="V2"))
        entry = db.get_entry("up1", "test")
        assert entry["title"] == "V2"

    def test_metadata_json_stored(self, db):
        db.upsert_entry(_make_entry("m1", metadata={"custom": "value"}))
        entry = db.get_entry("m1", "test")
        import json
        meta = json.loads(entry["metadata"])
        assert meta["custom"] == "value"

    def test_created_by_preserved_on_update(self, db):
        db.upsert_entry(_make_entry("cb1", created_by="alice"))
        db.upsert_entry(_make_entry("cb1", created_by="bob", modified_by="bob"))
        entry = db.get_entry("cb1", "test")
        assert entry["created_by"] == "alice"
        assert entry["modified_by"] == "bob"

    def test_null_tags_filtered(self, db):
        """None values in tags list should be skipped."""
        db.upsert_entry(_make_entry("nt1", tags=["valid", None, "also-valid"]))
        entry = db.get_entry("nt1", "test")
        assert sorted(entry["tags"]) == ["also-valid", "valid"]


class TestSyncTags:
    """Test tag sync behavior."""

    def test_tags_created(self, db):
        db.upsert_entry(_make_entry("t1", tags=["alpha", "beta"]))
        entry = db.get_entry("t1", "test")
        assert sorted(entry["tags"]) == ["alpha", "beta"]

    def test_tags_replaced_on_update(self, db):
        db.upsert_entry(_make_entry("t2", tags=["old"]))
        db.upsert_entry(_make_entry("t2", tags=["new1", "new2"]))
        entry = db.get_entry("t2", "test")
        assert sorted(entry["tags"]) == ["new1", "new2"]

    def test_shared_tags_reused(self, db):
        """Two entries sharing a tag should reference the same tag row."""
        db.upsert_entry(_make_entry("s1", tags=["shared"]))
        db.upsert_entry(_make_entry("s2", tags=["shared"]))
        e1 = db.get_entry("s1", "test")
        e2 = db.get_entry("s2", "test")
        assert "shared" in e1["tags"]
        assert "shared" in e2["tags"]


class TestSyncSources:
    """Test source sync behavior."""

    def test_sources_created(self, db):
        db.upsert_entry(_make_entry("src1", sources=[
            {"title": "Source A", "url": "https://a.com", "verified": True}
        ]))
        entry = db.get_entry("src1", "test")
        assert len(entry["sources"]) == 1
        assert entry["sources"][0]["title"] == "Source A"
        assert entry["sources"][0]["verified"] == 1

    def test_sources_replaced_on_update(self, db):
        db.upsert_entry(_make_entry("src2", sources=[{"title": "Old"}]))
        db.upsert_entry(_make_entry("src2", sources=[{"title": "New"}]))
        entry = db.get_entry("src2", "test")
        assert len(entry["sources"]) == 1
        assert entry["sources"][0]["title"] == "New"


class TestSyncLinks:
    """Test link sync behavior."""

    def test_links_created(self, db):
        db.upsert_entry(_make_entry("l1"))
        db.upsert_entry(_make_entry("l2", links=[
            {"target": "l1", "relation": "related_to"}
        ]))
        entry = db.get_entry("l2", "test")
        assert len(entry["links"]) == 1
        assert entry["links"][0]["target_id"] == "l1"

    def test_links_replaced_on_update(self, db):
        db.upsert_entry(_make_entry("la"))
        db.upsert_entry(_make_entry("lb"))
        db.upsert_entry(_make_entry("lc", links=[{"target": "la", "relation": "related_to"}]))
        db.upsert_entry(_make_entry("lc", links=[{"target": "lb", "relation": "caused_by"}]))
        entry = db.get_entry("lc", "test")
        assert len(entry["links"]) == 1
        assert entry["links"][0]["target_id"] == "lb"


class TestDeleteEntry:
    """Test delete_entry."""

    def test_delete_existing(self, db):
        db.upsert_entry(_make_entry("d1"))
        assert db.delete_entry("d1", "test") is True
        assert db.get_entry("d1", "test") is None

    def test_delete_nonexistent(self, db):
        assert db.delete_entry("nope", "test") is False


class TestListEntries:
    """Test list_entries ORM query."""

    def test_list_with_filters(self, db):
        db.upsert_entry(_make_entry("e1", entry_type="note", tags=["a"]))
        db.upsert_entry(_make_entry("e2", entry_type="event", tags=["b"]))
        db.upsert_entry(_make_entry("e3", entry_type="note", tags=["a"]))

        notes = db.list_entries(kb_name="test", entry_type="note")
        assert len(notes) == 2

        tagged = db.list_entries(kb_name="test", tag="a")
        assert len(tagged) == 2

    def test_list_pagination(self, db):
        for i in range(5):
            db.upsert_entry(_make_entry(f"p{i}"))
        page = db.list_entries(kb_name="test", limit=2, offset=0)
        assert len(page) == 2
        page2 = db.list_entries(kb_name="test", limit=2, offset=2)
        assert len(page2) == 2


class TestCountEntries:
    """Test count_entries."""

    def test_count_all(self, db):
        for i in range(3):
            db.upsert_entry(_make_entry(f"c{i}"))
        assert db.count_entries(kb_name="test") == 3

    def test_count_by_type(self, db):
        db.upsert_entry(_make_entry("ct1", entry_type="note"))
        db.upsert_entry(_make_entry("ct2", entry_type="event"))
        assert db.count_entries(kb_name="test", entry_type="note") == 1

    def test_count_by_tag(self, db):
        db.upsert_entry(_make_entry("cg1", tags=["x"]))
        db.upsert_entry(_make_entry("cg2", tags=["y"]))
        assert db.count_entries(kb_name="test", tag="x") == 1


class TestGetDistinctTypes:
    """Test get_distinct_types."""

    def test_distinct_types(self, db):
        db.upsert_entry(_make_entry("dt1", entry_type="note"))
        db.upsert_entry(_make_entry("dt2", entry_type="event"))
        db.upsert_entry(_make_entry("dt3", entry_type="note"))
        types = db.get_distinct_types(kb_name="test")
        assert sorted(types) == ["event", "note"]


class TestGetEntriesForIndexing:
    """Test get_entries_for_indexing."""

    def test_returns_indexing_data(self, db):
        db.upsert_entry(_make_entry("idx1", file_path="/a.md"))
        rows = db.get_entries_for_indexing("test")
        assert len(rows) == 1
        assert rows[0]["id"] == "idx1"
        assert rows[0]["file_path"] == "/a.md"
        assert "indexed_at" in rows[0]


class TestEntryRefs:
    """Test _sync_entry_refs via upsert_entry."""

    def test_refs_synced(self, db):
        db.upsert_entry(_make_entry("ref1"))
        db.upsert_entry(_make_entry("ref2", _refs=[
            {"target_id": "ref1", "field_name": "related_to", "target_type": "note"}
        ]))
        refs = db.get_refs_from("ref2", "test")
        assert len(refs) == 1
        assert refs[0]["id"] == "ref1"
