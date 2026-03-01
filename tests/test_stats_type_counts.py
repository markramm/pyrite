"""Tests for type_counts in stats endpoint."""
import pytest
from pyrite.storage.database import PyriteDB


@pytest.fixture
def db_with_types(tmp_path):
    db = PyriteDB(tmp_path / "test.db")
    db.register_kb(name="test", kb_type="generic", path=str(tmp_path))
    # Insert entries of different types
    for i, t in enumerate(["note", "note", "note", "event", "event", "person"]):
        db.upsert_entry({
            "id": f"entry-{i}",
            "kb_name": "test",
            "entry_type": t,
            "title": f"Entry {i}",
            "body": f"Body {i}",
        })
    return db


def test_get_type_counts_all(db_with_types):
    counts = db_with_types.get_type_counts()
    assert len(counts) == 3
    assert counts[0] == {"entry_type": "note", "count": 3}
    assert counts[1] == {"entry_type": "event", "count": 2}
    assert counts[2] == {"entry_type": "person", "count": 1}


def test_get_type_counts_by_kb(db_with_types):
    counts = db_with_types.get_type_counts("test")
    assert len(counts) == 3


def test_get_type_counts_empty_kb(db_with_types):
    db_with_types.register_kb(name="empty", kb_type="generic", path="/tmp/empty")
    counts = db_with_types.get_type_counts("empty")
    assert counts == []
