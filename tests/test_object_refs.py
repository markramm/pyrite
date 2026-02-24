"""Tests for typed object references (entry_ref table)."""

import tempfile
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB


class TestObjectRefs:
    """Tests for object-ref field indexing and reverse lookup."""

    @pytest.fixture
    def db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PyriteDB(db_path)
            yield db
            db.close()

    def test_entry_ref_table_exists(self, db):
        """entry_ref table should be created."""
        row = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entry_ref'"
        ).fetchone()
        assert row is not None

    def test_sync_entry_refs(self, db):
        """Upserting entry with _refs populates entry_ref table."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")
        entry_data = {
            "id": "meeting-1",
            "kb_name": "test-kb",
            "entry_type": "meeting",
            "title": "Sprint Review",
            "body": "Discussion notes",
            "tags": [],
            "sources": [],
            "links": [],
            "_refs": [
                {"target_id": "alice", "field_name": "organizer", "target_type": "person"},
                {"target_id": "bob", "field_name": "attendees", "target_type": "person"},
            ],
        }
        db.upsert_entry(entry_data)

        rows = db.conn.execute(
            "SELECT * FROM entry_ref WHERE source_id = 'meeting-1' AND source_kb = 'test-kb'"
        ).fetchall()
        assert len(rows) == 2

    def test_refs_to_reverse_lookup(self, db):
        """get_refs_to returns entries referencing a target."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")

        # Create target entry
        db.upsert_entry(
            {
                "id": "alice",
                "kb_name": "test-kb",
                "entry_type": "person",
                "title": "Alice",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )

        # Create source entry with ref to alice
        db.upsert_entry(
            {
                "id": "meeting-1",
                "kb_name": "test-kb",
                "entry_type": "meeting",
                "title": "Sprint Review",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
                "_refs": [
                    {"target_id": "alice", "field_name": "organizer", "target_type": "person"}
                ],
            }
        )

        refs = db.get_refs_to("alice", "test-kb")
        assert len(refs) == 1
        assert refs[0]["id"] == "meeting-1"
        assert refs[0]["field_name"] == "organizer"

    def test_refs_from_lookup(self, db):
        """get_refs_from returns entries referenced by a source."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")

        db.upsert_entry(
            {
                "id": "alice",
                "kb_name": "test-kb",
                "entry_type": "person",
                "title": "Alice",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )
        db.upsert_entry(
            {
                "id": "meeting-1",
                "kb_name": "test-kb",
                "entry_type": "meeting",
                "title": "Sprint Review",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
                "_refs": [
                    {"target_id": "alice", "field_name": "organizer", "target_type": "person"}
                ],
            }
        )

        refs = db.get_refs_from("meeting-1", "test-kb")
        assert len(refs) == 1
        assert refs[0]["id"] == "alice"
        assert refs[0]["field_name"] == "organizer"

    def test_refs_replaced_on_reindex(self, db):
        """Re-upserting entry replaces old refs."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "meeting-1",
                "kb_name": "test-kb",
                "entry_type": "meeting",
                "title": "Sprint",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
                "_refs": [
                    {"target_id": "alice", "field_name": "organizer", "target_type": "person"}
                ],
            }
        )

        # Re-upsert with different refs
        db.upsert_entry(
            {
                "id": "meeting-1",
                "kb_name": "test-kb",
                "entry_type": "meeting",
                "title": "Sprint",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
                "_refs": [{"target_id": "bob", "field_name": "organizer", "target_type": "person"}],
            }
        )

        rows = db.conn.execute(
            "SELECT target_id FROM entry_ref WHERE source_id = 'meeting-1'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["target_id"] == "bob"

    def test_refs_deleted_with_entry(self, db):
        """Deleting entry cascades to entry_ref."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "meeting-1",
                "kb_name": "test-kb",
                "entry_type": "meeting",
                "title": "Sprint",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
                "_refs": [
                    {"target_id": "alice", "field_name": "organizer", "target_type": "person"}
                ],
            }
        )
        db.delete_entry("meeting-1", "test-kb")

        rows = db.conn.execute("SELECT * FROM entry_ref WHERE source_id = 'meeting-1'").fetchall()
        assert len(rows) == 0

    def test_no_refs_when_none_provided(self, db):
        """Entry without _refs doesn't create entry_ref rows."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "note-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Just a note",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )

        rows = db.conn.execute("SELECT * FROM entry_ref WHERE source_id = 'note-1'").fetchall()
        assert len(rows) == 0
