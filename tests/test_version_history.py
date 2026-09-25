"""Tests for version history endpoints."""

import tempfile
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB


class TestVersionHistoryDB:
    """Test version history DB operations."""

    @pytest.fixture
    def db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PyriteDB(db_path)
            yield db
            db.close()

    def test_get_empty_versions(self, db):
        """get_entry_versions returns empty list for new entry."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Test",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )
        versions = db.get_entry_versions("entry-1", "test-kb")
        assert versions == []

    def test_upsert_and_get_versions(self, db):
        """Can insert and retrieve entry versions."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Test",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )

        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="abc123def456",
            author_name="Alice",
            author_email="alice@example.com",
            commit_date="2025-01-20T10:00:00",
            message="Initial commit",
            change_type="created",
        )
        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="def456abc789",
            author_name="Bob",
            author_email="bob@example.com",
            commit_date="2025-01-21T10:00:00",
            message="Updated content",
            change_type="modified",
        )

        versions = db.get_entry_versions("entry-1", "test-kb")
        assert len(versions) == 2
        # Ordered by commit_date DESC
        assert versions[0]["author_name"] == "Bob"
        assert versions[1]["author_name"] == "Alice"

    def test_versions_limit(self, db):
        """get_entry_versions respects limit."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Test",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )

        for i in range(5):
            db.upsert_entry_version(
                entry_id="entry-1",
                kb_name="test-kb",
                commit_hash=f"hash{i:040d}",
                author_name="Alice",
                author_email="alice@example.com",
                commit_date=f"2025-01-{20 + i:02d}T10:00:00",
                message=f"Commit {i}",
                change_type="modified",
            )

        versions = db.get_entry_versions("entry-1", "test-kb", limit=3)
        assert len(versions) == 3

    def test_entry_version_exists(self, db):
        """entry_version_exists is an exact existence check on
        (entry_id, kb_name, commit_hash) -- an indexed point lookup, not a
        full scan of the entry's recorded versions (#415 cold read)."""
        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Test",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )
        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="abc123def456",
            author_name="Alice",
            author_email="alice@example.com",
            commit_date="2025-01-20T10:00:00",
            message="Initial commit",
            change_type="created",
        )

        assert db.entry_version_exists("entry-1", "test-kb", "abc123def456") is True
        # Wrong entry, wrong KB, wrong hash -- each dimension must matter.
        assert db.entry_version_exists("entry-2", "test-kb", "abc123def456") is False
        assert db.entry_version_exists("entry-1", "other-kb", "abc123def456") is False
        assert db.entry_version_exists("entry-1", "test-kb", "0" * 40) is False

    def test_upsert_entry_version_stores_file_path(self, db):
        """A version records the path the entry had at that commit, so a
        rename doesn't strand earlier rows against a path that didn't exist
        yet (#432)."""
        from pyrite.storage.models import EntryVersion

        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Test",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )
        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="abc123def456",
            author_name="Alice",
            author_email="alice@example.com",
            commit_date="2025-01-20T10:00:00",
            message="Initial commit",
            change_type="created",
            file_path="/tmp/test/a.md",
        )

        row = db.session.query(EntryVersion).filter_by(commit_hash="abc123def456").first()
        assert row is not None
        assert row.file_path == "/tmp/test/a.md"

    def test_upsert_entry_version_backfills_missing_path_on_existing_row(self, db):
        """Re-running attribution indexing on a row recorded before #432
        (no path) must fill it in -- upsert_entry_version's existing
        skip-if-present behaviour would otherwise never repair old rows."""
        from pyrite.storage.models import EntryVersion

        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Test",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )
        # First recorded with no path (pre-#432 shape).
        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="abc123def456",
            author_name="Alice",
            author_email="alice@example.com",
            commit_date="2025-01-20T10:00:00",
            message="Initial commit",
            change_type="created",
        )
        # Re-run (e.g. `index build --with-attribution`), now supplying a path.
        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="abc123def456",
            author_name="Alice",
            author_email="alice@example.com",
            commit_date="2025-01-20T10:00:00",
            message="Initial commit",
            change_type="created",
            file_path="/tmp/test/a.md",
        )

        row = db.session.query(EntryVersion).filter_by(commit_hash="abc123def456").first()
        assert row is not None
        assert row.file_path == "/tmp/test/a.md"

    def test_upsert_entry_version_does_not_clobber_path_with_none(self, db):
        """A later re-run that doesn't supply a path (e.g. a caller still on
        the old signature) must not blank out a path already recorded."""
        from pyrite.storage.models import EntryVersion

        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Test",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )
        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="abc123def456",
            author_name="Alice",
            author_email="alice@example.com",
            commit_date="2025-01-20T10:00:00",
            message="Initial commit",
            change_type="created",
            file_path="/tmp/test/a.md",
        )
        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="abc123def456",
            author_name="Alice",
            author_email="alice@example.com",
            commit_date="2025-01-20T10:00:00",
            message="Initial commit",
            change_type="created",
        )

        row = db.session.query(EntryVersion).filter_by(commit_hash="abc123def456").first()
        assert row.file_path == "/tmp/test/a.md"

    def test_upsert_entry_version_does_not_overwrite_an_existing_path(self, db):
        """Once a version's path is recorded, a later call with a
        *different* path (e.g. a second, differently-configured indexing
        run) must not silently replace the one recorded at that commit --
        only a still-missing path is ever filled in."""
        from pyrite.storage.models import EntryVersion

        db.register_kb("test-kb", "generic", "/tmp/test", "")
        db.upsert_entry(
            {
                "id": "entry-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Test",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )
        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="abc123def456",
            author_name="Alice",
            author_email="alice@example.com",
            commit_date="2025-01-20T10:00:00",
            message="Initial commit",
            change_type="created",
            file_path="/tmp/test/a.md",
        )
        db.upsert_entry_version(
            entry_id="entry-1",
            kb_name="test-kb",
            commit_hash="abc123def456",
            author_name="Alice",
            author_email="alice@example.com",
            commit_date="2025-01-20T10:00:00",
            message="Initial commit",
            change_type="created",
            file_path="/tmp/test/DIFFERENT.md",
        )

        row = db.session.query(EntryVersion).filter_by(commit_hash="abc123def456").first()
        assert row.file_path == "/tmp/test/a.md"


class TestVersionHistoryAPI:
    """Test version history REST endpoints."""

    @pytest.fixture
    def client(self):
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
        from pyrite.server.api import create_app, get_config, get_db

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"
            kb_path = tmpdir / "notes"
            kb_path.mkdir()

            kb = KBConfig(name="test-kb", path=kb_path, kb_type=KBType.GENERIC)
            config = PyriteConfig(knowledge_bases=[kb], settings=Settings(index_path=db_path))

            db = PyriteDB(db_path)
            db.register_kb("test-kb", "generic", str(kb_path), "")

            # Create entry and versions
            db.upsert_entry(
                {
                    "id": "entry-1",
                    "kb_name": "test-kb",
                    "entry_type": "note",
                    "title": "Test Entry",
                    "body": "Content",
                    "tags": [],
                    "sources": [],
                    "links": [],
                }
            )
            db.upsert_entry_version(
                entry_id="entry-1",
                kb_name="test-kb",
                commit_hash="abc123def456789012345678901234567890",
                author_name="Alice",
                author_email="alice@example.com",
                commit_date="2025-01-20T10:00:00",
                message="Initial",
                change_type="created",
            )

            app = create_app(config)
            app.dependency_overrides[get_config] = lambda: config
            app.dependency_overrides[get_db] = lambda: db
            yield {"client": TestClient(app), "db": db}
            db.close()

    def test_get_versions(self, client):
        """GET /entries/{id}/versions returns version list."""
        resp = client["client"].get("/api/entries/entry-1/versions?kb=test-kb")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entry_id"] == "entry-1"
        assert data["kb_name"] == "test-kb"
        assert data["count"] == 1
        assert data["versions"][0]["commit_hash"] == "abc123def456789012345678901234567890"

    def test_get_versions_empty(self, client):
        """GET /entries/{id}/versions returns empty for entry without versions."""
        db = client["db"]

        db.upsert_entry(
            {
                "id": "entry-2",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "No Versions",
                "body": "",
                "tags": [],
                "sources": [],
                "links": [],
            }
        )

        resp = client["client"].get("/api/entries/entry-2/versions?kb=test-kb")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
        assert resp.json()["versions"] == []
