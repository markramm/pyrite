"""Tests for Block References Phase 1 — API endpoint."""

import tempfile
from pathlib import Path

import pytest


class TestBlocksAPI:
    """Tests for block reference REST endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client with entry and block data populated by indexer."""
        pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
        from pyrite.models.core_types import NoteEntry
        from pyrite.server.api import create_app
        from pyrite.storage.database import PyriteDB
        from pyrite.storage.index import IndexManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"
            kb_path = tmpdir / "kb"
            kb_path.mkdir()

            # Create a note — the indexer will auto-extract blocks from body
            note = NoteEntry(
                id="test-note",
                title="Test Note",
                body="# Introduction\nHello world\n\n## Details\nSome details here",
                tags=["test"],
            )
            note.save(kb_path / "test-note.md")

            kb_config = KBConfig(name="test-kb", path=kb_path, kb_type=KBType.GENERIC)
            config = PyriteConfig(
                knowledge_bases=[kb_config],
                settings=Settings(index_path=db_path),
            )
            db = PyriteDB(db_path)
            IndexManager(db, config).index_all()

            import pyrite.server.api as api_module

            api_module._config = config
            api_module._db = db

            app = create_app(config)
            yield TestClient(app)

    def test_get_entry_blocks_endpoint(self, client):
        """GET /entries/{id}/blocks returns blocks."""
        resp = client.get("/api/entries/test-note/blocks?kb=test-kb")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entry_id"] == "test-note"
        assert data["kb_name"] == "test-kb"
        # Indexer extracts blocks from markdown: 2 headings + 2 paragraphs
        assert data["total"] == 4
        assert len(data["blocks"]) == 4
        # Check ordering by position
        positions = [b["position"] for b in data["blocks"]]
        assert positions == sorted(positions)
        # Verify block types are present
        block_types = {b["block_type"] for b in data["blocks"]}
        assert "heading" in block_types
        assert "paragraph" in block_types

    def test_get_entry_blocks_filter_by_heading(self, client):
        """Filter by heading parameter."""
        resp = client.get("/api/entries/test-note/blocks?kb=test-kb&heading=Introduction")
        assert resp.status_code == 200
        data = resp.json()
        # "Introduction" heading block + "Hello world" paragraph under it
        assert data["total"] == 2
        for block in data["blocks"]:
            assert block["heading"] == "Introduction"

    def test_get_entry_blocks_filter_by_type(self, client):
        """Filter by block_type parameter."""
        resp = client.get("/api/entries/test-note/blocks?kb=test-kb&block_type=paragraph")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for block in data["blocks"]:
            assert block["block_type"] == "paragraph"

    def test_get_entry_blocks_not_found(self, client):
        """404 for nonexistent entry."""
        resp = client.get("/api/entries/nonexistent/blocks?kb=test-kb")
        assert resp.status_code == 404

    def test_blocks_endpoint_registered(self, client):
        """Verify the endpoint is discoverable via OpenAPI."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/entries/{entry_id}/blocks" in paths
