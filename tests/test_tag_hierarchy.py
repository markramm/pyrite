"""Tests for tag hierarchy and prefix search."""

import tempfile
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB


class TestTagHierarchy:
    """Tests for hierarchical tag tree and prefix matching."""

    @pytest.fixture
    def db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = PyriteDB(db_path)
            db.register_kb("test-kb", "generic", "/tmp/test", "")
            yield db
            db.close()

    def _create_entry(self, db, entry_id: str, tags: list[str]):
        db.upsert_entry(
            {
                "id": entry_id,
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": f"Entry {entry_id}",
                "body": "",
                "tags": tags,
                "sources": [],
                "links": [],
            }
        )

    def test_flat_tags_still_work(self, db):
        """Flat tags without / work as before."""
        self._create_entry(db, "e1", ["python", "rust"])
        tags = db.get_tags_as_dicts("test-kb")
        names = [t["name"] for t in tags]
        assert "python" in names
        assert "rust" in names

    def test_tag_tree_builds_hierarchy(self, db):
        """Tags with / build correct tree structure."""
        self._create_entry(db, "e1", ["lang/python", "lang/rust"])
        self._create_entry(db, "e2", ["lang/python", "tools/cli"])
        self._create_entry(db, "e3", ["lang/python/flask"])

        tree = db.get_tag_tree("test-kb")

        # Should have two root nodes: lang and tools
        root_names = [n["name"] for n in tree]
        assert "lang" in root_names
        assert "tools" in root_names

        # lang should have children: python and rust
        lang = next(n for n in tree if n["name"] == "lang")
        child_names = [c["name"] for c in lang["children"]]
        assert "python" in child_names
        assert "rust" in child_names

        # lang/python should have count 2 (two entries tagged lang/python)
        python = next(c for c in lang["children"] if c["name"] == "python")
        assert python["count"] == 2

    def test_prefix_search_includes_children(self, db):
        """Searching by prefix includes entries with child tags."""
        self._create_entry(db, "e1", ["lang/python"])
        self._create_entry(db, "e2", ["lang/python/flask"])
        self._create_entry(db, "e3", ["lang/rust"])
        self._create_entry(db, "e4", ["tools/cli"])

        results = db.search_by_tag_prefix("lang/python", "test-kb")
        ids = [r["id"] for r in results]
        assert "e1" in ids
        assert "e2" in ids
        assert "e3" not in ids
        assert "e4" not in ids

    def test_prefix_search_at_root(self, db):
        """Searching by root prefix includes all under that root."""
        self._create_entry(db, "e1", ["lang/python"])
        self._create_entry(db, "e2", ["lang/rust"])
        self._create_entry(db, "e3", ["tools/cli"])

        results = db.search_by_tag_prefix("lang", "test-kb")
        ids = [r["id"] for r in results]
        assert "e1" in ids
        assert "e2" in ids
        assert "e3" not in ids

    def test_empty_tree_for_no_tags(self, db):
        """Empty tree when no tags exist."""
        tree = db.get_tag_tree("test-kb")
        assert tree == []

    def test_tag_tree_deep_nesting(self, db):
        """Tags with 3+ levels build correct deep tree."""
        self._create_entry(db, "e1", ["a/b/c", "a/b/d", "a/e"])
        tree = db.get_tag_tree("test-kb")

        a = next(n for n in tree if n["name"] == "a")
        assert len(a["children"]) == 2  # b and e

        b = next(c for c in a["children"] if c["name"] == "b")
        assert len(b["children"]) == 2  # c and d

        c = next(c for c in b["children"] if c["name"] == "c")
        assert c["count"] == 1


class TestTagTreeAPI:
    """Test tag tree REST endpoint."""

    @pytest.fixture
    def client(self):
        fastapi = pytest.importorskip("fastapi")  # noqa: F841
        from fastapi.testclient import TestClient

        import pyrite.server.api as api_module
        from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
        from pyrite.server.api import create_app
        from pyrite.storage.database import PyriteDB

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"
            kb_path = tmpdir / "notes"
            kb_path.mkdir()

            kb = KBConfig(name="test-notes", path=kb_path, kb_type=KBType.GENERIC)
            config = PyriteConfig(knowledge_bases=[kb], settings=Settings(index_path=db_path))

            db = PyriteDB(db_path)
            db.register_kb("test-notes", "generic", str(kb_path), "")

            # Create tagged entries
            for i, tags in enumerate([["lang/python"], ["lang/rust"], ["tools/cli"]]):
                db.upsert_entry(
                    {
                        "id": f"entry-{i}",
                        "kb_name": "test-notes",
                        "entry_type": "note",
                        "title": f"Entry {i}",
                        "body": "",
                        "tags": tags,
                        "sources": [],
                        "links": [],
                    }
                )

            api_module._config = config
            api_module._db = db
            api_module._kb_service = None
            app = create_app(config)
            yield TestClient(app)
            db.close()

            # Reset globals
            api_module._config = None
            api_module._db = None
            api_module._kb_service = None

    def test_get_tag_tree(self, client):
        """GET /tags/tree returns hierarchical tree."""
        resp = client.get("/api/tags/tree?kb=test-notes")
        assert resp.status_code == 200
        data = resp.json()
        assert "tree" in data
        root_names = [n["name"] for n in data["tree"]]
        assert "lang" in root_names
        assert "tools" in root_names

    def test_get_tags_with_prefix(self, client):
        """GET /tags?prefix=lang filters tags."""
        resp = client.get("/api/tags?kb=test-notes&prefix=lang")
        assert resp.status_code == 200
        data = resp.json()
        for tag in data["tags"]:
            assert tag["name"].startswith("lang")
