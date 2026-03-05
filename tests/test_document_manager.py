"""Tests for DocumentManager — ODM write-path coordination (#100 Phase 5)."""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.models.factory import build_entry
from pyrite.schema.field_schema import TypeSchema
from pyrite.schema.kb_schema import KBSchema
from pyrite.storage.database import PyriteDB
from pyrite.storage.document_manager import DocumentManager
from pyrite.storage.index import IndexManager


@pytest.fixture
def setup(tmp_path):
    """Create a minimal KB, DB, and DocumentManager."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()

    kb = KBConfig(name="test", path=kb_path, kb_type="generic")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    index_mgr = IndexManager(db, config)
    doc_mgr = DocumentManager(db, index_mgr)

    yield {"kb": kb, "config": config, "db": db, "doc_mgr": doc_mgr, "kb_path": kb_path}
    db.close()


def test_save_entry_writes_file_and_indexes(setup):
    """save_entry writes the file to disk and indexes it in the DB."""
    doc_mgr = setup["doc_mgr"]
    kb = setup["kb"]
    db = setup["db"]

    entry = build_entry("note", entry_id="hello-world", title="Hello World", body="Test body")
    file_path = doc_mgr.save_entry(entry, "test", kb)

    # File exists on disk
    assert file_path.exists()
    assert "Hello World" in file_path.read_text()

    # Entry is in the index
    row = db.get_entry("hello-world", "test")
    assert row is not None
    assert row["title"] == "Hello World"


def test_save_entry_registers_kb(setup):
    """save_entry registers the KB in the database."""
    doc_mgr = setup["doc_mgr"]
    kb = setup["kb"]
    db = setup["db"]

    entry = build_entry("note", entry_id="reg-test", title="Reg Test", body="")
    doc_mgr.save_entry(entry, "test", kb)

    stats = db.get_kb_stats("test")
    assert stats is not None


def test_delete_entry_removes_file_and_index(setup):
    """delete_entry removes the file from disk and the entry from the index."""
    doc_mgr = setup["doc_mgr"]
    kb = setup["kb"]
    db = setup["db"]

    entry = build_entry("note", entry_id="to-delete", title="To Delete", body="bye")
    file_path = doc_mgr.save_entry(entry, "test", kb)
    assert file_path.exists()

    deleted = doc_mgr.delete_entry("to-delete", "test", kb)
    assert deleted is True
    assert not file_path.exists()
    assert db.get_entry("to-delete", "test") is None


def test_index_entry_without_file_save(setup):
    """index_entry indexes an entry without writing to disk."""
    doc_mgr = setup["doc_mgr"]
    kb = setup["kb"]
    db = setup["db"]
    kb_path = setup["kb_path"]

    # Register KB first (index_entry is index-only, doesn't register)
    db.register_kb(name="test", kb_type="generic", path=str(kb_path))

    # Manually create a file on disk
    file_path = kb_path / "manual-entry.md"
    file_path.write_text("---\ntype: note\ntitle: Manual\n---\nManual body\n")

    entry = build_entry("note", entry_id="manual-entry", title="Manual", body="Manual body")
    doc_mgr.index_entry(entry, "test", file_path)

    row = db.get_entry("manual-entry", "test")
    assert row is not None
    assert row["title"] == "Manual"


def test_save_entry_idempotent(setup):
    """Calling save_entry twice doesn't fail — second call updates."""
    doc_mgr = setup["doc_mgr"]
    kb = setup["kb"]
    db = setup["db"]

    entry = build_entry("note", entry_id="idem-test", title="Version 1", body="v1")
    doc_mgr.save_entry(entry, "test", kb)

    entry.title = "Version 2"
    entry.body = "v2"
    file_path = doc_mgr.save_entry(entry, "test", kb)

    assert file_path.exists()
    assert "Version 2" in file_path.read_text()

    row = db.get_entry("idem-test", "test")
    assert row["title"] == "Version 2"


# --- File movement on template path change ---


@pytest.fixture
def template_setup(tmp_path):
    """Create a KB with templated subdirectory for note type."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()

    schema = KBSchema(
        types={
            "note": TypeSchema(name="note", subdirectory="notes/{status}"),
        }
    )

    kb = KBConfig(name="test", path=kb_path, kb_type="generic")
    kb._schema_cache = schema

    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    index_mgr = IndexManager(db, config)
    doc_mgr = DocumentManager(db, index_mgr)

    yield {"kb": kb, "config": config, "db": db, "doc_mgr": doc_mgr, "kb_path": kb_path}
    db.close()


def test_save_entry_moves_file_on_field_change(template_setup):
    """When a templated field changes, saving moves the file to the new path."""
    doc_mgr = template_setup["doc_mgr"]
    kb = template_setup["kb"]
    kb_path = template_setup["kb_path"]

    entry = build_entry("note", entry_id="move-test", title="Move Test", body="body")
    entry.metadata["status"] = "active"
    first_path = doc_mgr.save_entry(entry, "test", kb)

    assert first_path.exists()
    assert "notes/active" in str(first_path)

    # Change status → should move file
    entry.metadata["status"] = "done"
    second_path = doc_mgr.save_entry(entry, "test", kb)

    assert second_path.exists()
    assert "notes/done" in str(second_path)
    assert not first_path.exists(), "Old file should be removed"


def test_save_entry_no_move_when_path_unchanged(template_setup):
    """When the resolved path hasn't changed, no move occurs."""
    doc_mgr = template_setup["doc_mgr"]
    kb = template_setup["kb"]

    entry = build_entry("note", entry_id="stay-test", title="Stay Test", body="body")
    entry.metadata["status"] = "active"
    first_path = doc_mgr.save_entry(entry, "test", kb)

    # Save again with same status
    entry.title = "Stay Test Updated"
    second_path = doc_mgr.save_entry(entry, "test", kb)

    assert first_path == second_path
    assert second_path.exists()
