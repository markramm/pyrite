"""Tests for the site cache renderer."""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.site_cache import SiteCacheService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def cache_env(tmp_path):
    """Create a minimal Pyrite environment for cache testing."""
    kb = KBConfig(name="test-kb", path=tmp_path / "kb", kb_type="generic")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    db.register_kb("test-kb", "generic", str(tmp_path / "kb"), "A test KB")

    # Add some entries
    db.upsert_entry({
        "id": "hello-world",
        "kb_name": "test-kb",
        "entry_type": "note",
        "title": "Hello World",
        "body": "This is a test entry with a [[wikilink]].",
        "summary": "A test entry",
        "tags": ["test", "demo"],
        "sources": [],
        "links": [{"target": "wikilink", "relation": "related_to"}],
        "metadata": {},
    })
    db.upsert_entry({
        "id": "wikilink",
        "kb_name": "test-kb",
        "entry_type": "concept",
        "title": "Wikilink Target",
        "body": "This is the target of a wikilink.",
        "summary": "",
        "tags": [],
        "sources": [],
        "links": [],
        "metadata": {},
    })

    svc = SiteCacheService(config, db)
    yield {"svc": svc, "db": db, "cache_dir": svc.cache_dir}
    db.close()


class TestSiteCacheRenderAll:
    def test_render_creates_files(self, cache_env):
        stats = cache_env["svc"].render_all()
        assert stats["kbs"] == 1
        assert stats["entries"] == 2
        assert stats["errors"] == 0

    def test_landing_page_created(self, cache_env):
        cache_env["svc"].render_all()
        landing = cache_env["cache_dir"] / "index.html"
        assert landing.exists()
        html = landing.read_text()
        assert "test-kb" in html
        assert "2 entries" in html

    def test_kb_index_created(self, cache_env):
        cache_env["svc"].render_all()
        kb_index = cache_env["cache_dir"] / "test-kb" / "index.html"
        assert kb_index.exists()
        html = kb_index.read_text()
        assert "Hello World" in html
        assert "Wikilink Target" in html

    def test_entry_page_created(self, cache_env):
        cache_env["svc"].render_all()
        entry_page = cache_env["cache_dir"] / "test-kb" / "hello-world.html"
        assert entry_page.exists()
        html = entry_page.read_text()
        assert "Hello World" in html
        assert "test entry" in html
        assert "application/ld+json" in html

    def test_wikilinks_resolved(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert '/site/test-kb/wikilink' in html

    def test_tags_rendered(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert "test" in html
        assert "demo" in html

    def test_backlinks_rendered(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "wikilink.html").read_text()
        # hello-world links to wikilink, so wikilink should show a backlink
        assert "Hello World" in html


class TestSiteCacheInvalidation:
    def test_invalidate_entry(self, cache_env):
        cache_env["svc"].render_all()
        path = cache_env["cache_dir"] / "test-kb" / "hello-world.html"
        assert path.exists()
        cache_env["svc"].invalidate_entry("hello-world", "test-kb")
        assert not path.exists()

    def test_invalidate_kb(self, cache_env):
        cache_env["svc"].render_all()
        kb_dir = cache_env["cache_dir"] / "test-kb"
        assert kb_dir.exists()
        cache_env["svc"].invalidate_kb("test-kb")
        assert not kb_dir.exists()

    def test_render_single_entry(self, cache_env):
        result = cache_env["svc"].render_entry_by_id("hello-world", "test-kb")
        assert result is True
        path = cache_env["cache_dir"] / "test-kb" / "hello-world.html"
        assert path.exists()
