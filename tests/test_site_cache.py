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


    def test_entry_has_canonical_url(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert 'rel="canonical"' in html
        assert '/site/test-kb/hello-world' in html

    def test_entry_has_reading_time(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert "min read" in html

    def test_entry_has_robots_meta(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert 'name="robots"' in html
        assert "index, follow" in html


class TestXSSPrevention:
    """Verify that malicious content is properly escaped in rendered HTML."""

    def test_title_escaped_in_page_title(self, cache_env):
        """XSS via entry title injecting into <title> tag."""
        cache_env["db"].upsert_entry({
            "id": "xss-title",
            "kb_name": "test-kb",
            "entry_type": "note",
            "title": '</title><script>alert("xss")</script>',
            "body": "Safe body.",
            "summary": "Safe summary",
            "tags": [],
            "sources": [],
            "links": [],
            "metadata": {},
        })
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-title.html").read_text()
        # The <title> tag should contain escaped content, not raw script tags
        import re
        title_match = re.search(r'<title>(.*?)</title>', html)
        assert title_match, "No <title> tag found"
        title_content = title_match.group(1)
        assert "<script>" not in title_content
        assert "&lt;script&gt;" in title_content

    def test_title_escaped_in_og_meta(self, cache_env):
        """XSS via entry title breaking out of og:title content attribute."""
        cache_env["db"].upsert_entry({
            "id": "xss-og",
            "kb_name": "test-kb",
            "entry_type": "note",
            "title": 'Evil" onload="alert(1)',
            "body": "Safe body.",
            "summary": "Safe summary",
            "tags": [],
            "sources": [],
            "links": [],
            "metadata": {},
        })
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-og.html").read_text()
        # The raw quote should be escaped in the og:title attribute
        assert 'content="Evil" onload' not in html
        assert "&quot;" in html

    def test_markdown_link_javascript_url_blocked(self, cache_env):
        """XSS via javascript: URL in markdown link."""
        cache_env["db"].upsert_entry({
            "id": "xss-jslink",
            "kb_name": "test-kb",
            "entry_type": "note",
            "title": "JS Link Test",
            "body": 'Click [here](javascript:alert(1)) for evil.',
            "summary": "",
            "tags": [],
            "sources": [],
            "links": [],
            "metadata": {},
        })
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-jslink.html").read_text()
        # The article body should not contain a javascript: link
        import re
        article = re.search(r'<article>(.*?)</article>', html, re.DOTALL)
        assert article, "No <article> tag found"
        assert 'href="javascript:' not in article.group(1)

    def test_markdown_link_text_escaped(self, cache_env):
        """XSS via HTML in markdown link text."""
        cache_env["db"].upsert_entry({
            "id": "xss-linktext",
            "kb_name": "test-kb",
            "entry_type": "note",
            "title": "Link Text XSS",
            "body": 'See [<img src=x onerror=alert(1)>](https://example.com) here.',
            "summary": "",
            "tags": [],
            "sources": [],
            "links": [],
            "metadata": {},
        })
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-linktext.html").read_text()
        import re
        article = re.search(r'<article>(.*?)</article>', html, re.DOTALL)
        assert article, "No <article> tag found"
        body = article.group(1)
        # The raw <img> tag should be escaped, not rendered as an element
        assert "<img " not in body
        assert "&lt;img" in body  # Should be escaped

    def test_esc_handles_single_quotes(self, cache_env):
        """_esc should also escape single quotes for attribute safety."""
        from pyrite.services.site_cache import _esc
        result = _esc("it's a test")
        assert "'" not in result or "&#39;" in result or "&apos;" in result


class TestPathTraversalPrevention:
    """Entry IDs with path traversal must not write files outside the cache dir."""

    def test_entry_id_with_path_traversal_stays_inside_cache(self, cache_env):
        cache_env["db"].upsert_entry({
            "id": "../../etc/evil",
            "kb_name": "test-kb",
            "entry_type": "note",
            "title": "Evil Entry",
            "body": "pwned",
            "summary": "",
            "tags": [],
            "sources": [],
            "links": [],
            "metadata": {},
        })
        cache_env["svc"].render_all()

        cache_dir = cache_env["cache_dir"]
        kb_dir = cache_dir / "test-kb"

        # Verify no file was written at the traversed path
        traversed = (kb_dir / "../../etc/evil.html").resolve()
        if traversed.exists():
            assert traversed.is_relative_to(cache_dir.resolve()), \
                f"Path traversal escape: {traversed} is outside {cache_dir}"

        # All HTML files under the kb_dir must have resolved paths inside cache_dir
        for f in kb_dir.iterdir():
            assert f.resolve().is_relative_to(cache_dir.resolve()), \
                f"File {f} escaped the cache directory"

        # The sanitized file should exist with a safe name (no slashes/dots)
        html_files = [f.name for f in kb_dir.iterdir() if f.suffix == ".html"]
        for name in html_files:
            assert ".." not in name, f"Filename contains '..': {name}"
            assert "/" not in name, f"Filename contains '/': {name}"


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
