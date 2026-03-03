"""Tests for protocol-aware cross-type queries (ADR-0017)."""

import tempfile
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB


@pytest.fixture
def db():
    """Create a temporary database with protocol-column entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = PyriteDB(db_path)
        db.register_kb("kb-a", "generic", "/tmp/a", "KB A")
        db.register_kb("kb-b", "generic", "/tmp/b", "KB B")

        # Task entry: assigned, with due_date, status, priority
        db.upsert_entry({
            "id": "task-1",
            "kb_name": "kb-a",
            "entry_type": "task",
            "title": "Investigate leads",
            "body": "",
            "assignee": "agent:alpha",
            "status": "in_progress",
            "due_date": "2026-02-01",
            "priority": 3,
            "tags": [],
            "sources": [],
            "links": [],
        })
        # Task in different KB, same assignee, done
        db.upsert_entry({
            "id": "task-2",
            "kb_name": "kb-b",
            "entry_type": "task",
            "title": "Write report",
            "body": "",
            "assignee": "agent:alpha",
            "status": "done",
            "due_date": "2026-03-01",
            "tags": [],
            "sources": [],
            "links": [],
        })
        # Event entry: has location, status
        db.upsert_entry({
            "id": "event-1",
            "kb_name": "kb-a",
            "entry_type": "event",
            "title": "Board meeting",
            "body": "",
            "status": "confirmed",
            "location": "New York City Hall",
            "date": "2026-01-15",
            "tags": [],
            "sources": [],
            "links": [],
        })
        # Backlog item: assigned, open, with location
        db.upsert_entry({
            "id": "backlog-1",
            "kb_name": "kb-b",
            "entry_type": "backlog_item",
            "title": "Fix login bug",
            "body": "",
            "assignee": "bob",
            "status": "open",
            "location": "New York office",
            "due_date": "2026-01-15",
            "tags": [],
            "sources": [],
            "links": [],
        })
        # Entry with no due_date (should not appear in overdue)
        db.upsert_entry({
            "id": "note-1",
            "kb_name": "kb-a",
            "entry_type": "note",
            "title": "Random note",
            "body": "",
            "tags": [],
            "sources": [],
            "links": [],
        })

        yield db
        db.close()


class TestFindByAssignee:
    def test_find_all_for_assignee(self, db):
        rows = db.find_by_assignee("agent:alpha")
        assert len(rows) == 2
        titles = {r["title"] for r in rows}
        assert titles == {"Investigate leads", "Write report"}

    def test_filter_by_kb(self, db):
        rows = db.find_by_assignee("agent:alpha", kb_name="kb-a")
        assert len(rows) == 1
        assert rows[0]["title"] == "Investigate leads"

    def test_filter_by_status(self, db):
        rows = db.find_by_assignee("agent:alpha", status="done")
        assert len(rows) == 1
        assert rows[0]["title"] == "Write report"

    def test_no_results(self, db):
        rows = db.find_by_assignee("nobody")
        assert rows == []


class TestFindOverdue:
    def test_find_overdue_default(self, db):
        # as_of defaults to today (2026-03-03), so anything before that is overdue
        rows = db.find_overdue()
        # task-1 (due 2026-02-01, in_progress) and backlog-1 (due 2026-01-15, open)
        titles = {r["title"] for r in rows}
        assert "Investigate leads" in titles
        assert "Fix login bug" in titles
        # task-2 is done, should NOT appear even though due_date < today
        assert "Write report" not in titles

    def test_find_overdue_as_of(self, db):
        # Only things due before 2026-01-20
        rows = db.find_overdue(as_of="2026-01-20")
        assert len(rows) == 1
        assert rows[0]["title"] == "Fix login bug"

    def test_find_overdue_with_kb(self, db):
        rows = db.find_overdue(kb_name="kb-a")
        titles = {r["title"] for r in rows}
        assert "Investigate leads" in titles
        assert "Fix login bug" not in titles


class TestFindByStatus:
    def test_find_by_status(self, db):
        rows = db.find_by_status("confirmed")
        assert len(rows) == 1
        assert rows[0]["title"] == "Board meeting"

    def test_find_by_status_with_type(self, db):
        rows = db.find_by_status("open", entry_type="backlog_item")
        assert len(rows) == 1
        assert rows[0]["title"] == "Fix login bug"

    def test_find_by_status_cross_type(self, db):
        # "in_progress" only task-1
        rows = db.find_by_status("in_progress")
        assert len(rows) == 1
        assert rows[0]["title"] == "Investigate leads"


class TestFindByLocation:
    def test_find_by_location_substring(self, db):
        rows = db.find_by_location("New York")
        assert len(rows) == 2
        titles = {r["title"] for r in rows}
        assert titles == {"Board meeting", "Fix login bug"}

    def test_find_by_location_exact(self, db):
        rows = db.find_by_location("City Hall")
        assert len(rows) == 1
        assert rows[0]["title"] == "Board meeting"

    def test_find_by_location_with_kb(self, db):
        rows = db.find_by_location("New York", kb_name="kb-b")
        assert len(rows) == 1
        assert rows[0]["title"] == "Fix login bug"

    def test_no_results(self, db):
        rows = db.find_by_location("Tokyo")
        assert rows == []
