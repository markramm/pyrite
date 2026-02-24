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


class TestVersionHistoryAPI:
    """Test version history REST endpoints."""

    @pytest.fixture
    def client(self):
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        import pyrite.server.api as api_module
        from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
        from pyrite.server.api import create_app

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

            api_module._config = config
            api_module._db = db
            app = create_app(config)
            yield TestClient(app)
            db.close()

    def test_get_versions(self, client):
        """GET /entries/{id}/versions returns version list."""
        resp = client.get("/api/entries/entry-1/versions?kb=test-kb")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entry_id"] == "entry-1"
        assert data["kb_name"] == "test-kb"
        assert data["count"] == 1
        assert data["versions"][0]["commit_hash"] == "abc123def456789012345678901234567890"

    def test_get_versions_empty(self, client):
        """GET /entries/{id}/versions returns empty for entry without versions."""
        import pyrite.server.api as api_module

        api_module._db.upsert_entry(
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

        resp = client.get("/api/entries/entry-2/versions?kb=test-kb")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
        assert resp.json()["versions"] == []
