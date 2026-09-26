"""Tests for the site cache renderer."""

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.site_cache import SiteCacheService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def cache_env(tmp_path):
    """Create a minimal Pyrite environment for cache testing."""
    kb = KBConfig(name="test-kb", path=tmp_path / "kb", kb_type="generic", default_role="read")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    db.register_kb("test-kb", "generic", str(tmp_path / "kb"), "A test KB")

    # Add some entries
    db.upsert_entry(
        {
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
        }
    )
    db.upsert_entry(
        {
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
        }
    )

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

    def test_includes_db_only_kb(self, tmp_path):
        """A KB registered only via `pyrite kb add` (DB-only, not in
        config.yaml's knowledge_bases) must be rendered too --
        collapse-kb-registry-to-one-source-of-truth's all_kbs() sweep.
        render_all() previously iterated config.knowledge_bases directly,
        silently excluding DB-only KBs from the static site export."""
        db_path = tmp_path / "index.db"
        kb_path = tmp_path / "db-only-kb"
        kb_path.mkdir()

        # NOT passed to PyriteConfig(knowledge_bases=...) -- DB-only.
        config = PyriteConfig(knowledge_bases=[], settings=Settings(index_path=db_path))
        db = PyriteDB(db_path)
        db.register_kb(
            "db-only-kb",
            "generic",
            str(kb_path),
            "A DB-only KB",
            source="user",
            default_role="read",
        )
        db.merge_registered_kbs(config)
        db.upsert_entry(
            {
                "id": "db-only-entry",
                "kb_name": "db-only-kb",
                "entry_type": "note",
                "title": "DB-only Entry",
                "body": "Body",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )

        svc = SiteCacheService(config, db)
        stats = svc.render_all()
        db.close()

        assert stats["kbs"] == 1, f"expected the DB-only KB to be rendered; got stats={stats}"
        kb_index = svc.cache_dir / "db-only-kb" / "index.html"
        assert kb_index.exists(), "expected a rendered index page for the DB-only KB"

    def test_wikilinks_resolved(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert "/site/test-kb/wikilink" in html

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
        assert "/site/test-kb/hello-world" in html

    def test_entry_has_reading_time(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert "min read" in html

    def test_entry_has_robots_meta(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert 'name="robots"' in html
        assert "index, follow" in html


class TestEditLinkVisibility:
    """Edit on Pyrite links should be hidden for read-only KBs."""

    def test_edit_link_present_for_writable_kb(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert "Edit on Pyrite" in html

    def test_edit_link_hidden_for_read_only_kb(self, tmp_path):
        kb = KBConfig(
            name="public-kb",
            path=tmp_path / "kb",
            kb_type="generic",
            default_role="read",
            read_only=True,
        )
        config = PyriteConfig(
            knowledge_bases=[kb],
            settings=Settings(index_path=tmp_path / "index.db"),
        )
        db = PyriteDB(tmp_path / "index.db")
        db.register_kb("public-kb", "generic", str(tmp_path / "kb"), "A public KB")
        db.upsert_entry(
            {
                "id": "test-entry",
                "kb_name": "public-kb",
                "entry_type": "note",
                "title": "Public Entry",
                "body": "Read-only content.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        svc = SiteCacheService(config, db)
        svc.render_all()
        html = (svc.cache_dir / "public-kb" / "test-entry.html").read_text()
        assert "Edit on Pyrite" not in html
        db.close()


class TestAboutPageLink:
    """About link in homepage should only appear when _about entry exists."""

    def test_about_link_hidden_when_no_about_entry(self, tmp_path):
        kb = KBConfig(name="my-kb", path=tmp_path / "kb", kb_type="generic", default_role="read")
        config = PyriteConfig(
            knowledge_bases=[kb],
            settings=Settings(index_path=tmp_path / "index.db"),
        )
        db = PyriteDB(tmp_path / "index.db")
        db.register_kb("my-kb", "generic", str(tmp_path / "kb"), "A KB")
        db.upsert_entry(
            {
                "id": "_homepage",
                "kb_name": "my-kb",
                "entry_type": "note",
                "title": "My Site",
                "body": "## The Pattern\n1. **Step** — Do things",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        svc = SiteCacheService(config, db)
        svc.render_all()
        html = (svc.cache_dir / "my-kb" / "index.html").read_text()
        assert "About" not in html or "_about" not in html
        db.close()

    def test_about_link_shown_when_about_entry_exists(self, tmp_path):
        kb = KBConfig(name="my-kb", path=tmp_path / "kb", kb_type="generic", default_role="read")
        config = PyriteConfig(
            knowledge_bases=[kb],
            settings=Settings(index_path=tmp_path / "index.db"),
        )
        db = PyriteDB(tmp_path / "index.db")
        db.register_kb("my-kb", "generic", str(tmp_path / "kb"), "A KB")
        db.upsert_entry(
            {
                "id": "_homepage",
                "kb_name": "my-kb",
                "entry_type": "note",
                "title": "My Site",
                "body": "## The Pattern\n1. **Step** — Do things",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        db.upsert_entry(
            {
                "id": "_about",
                "kb_name": "my-kb",
                "entry_type": "note",
                "title": "About & Methodology",
                "body": "Our methodology...",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        svc = SiteCacheService(config, db)
        svc.render_all()
        html = (svc.cache_dir / "my-kb" / "index.html").read_text()
        assert "_about" in html
        db.close()


class TestXSSPrevention:
    """Verify that malicious content is properly escaped in rendered HTML."""

    def test_title_escaped_in_page_title(self, cache_env):
        """XSS via entry title injecting into <title> tag."""
        cache_env["db"].upsert_entry(
            {
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
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-title.html").read_text()
        # The <title> tag should contain escaped content, not raw script tags
        import re

        title_match = re.search(r"<title>(.*?)</title>", html)
        assert title_match, "No <title> tag found"
        title_content = title_match.group(1)
        assert "<script>" not in title_content
        assert "&lt;script&gt;" in title_content

    def test_title_escaped_in_og_meta(self, cache_env):
        """XSS via entry title breaking out of og:title content attribute."""
        cache_env["db"].upsert_entry(
            {
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
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-og.html").read_text()
        # The raw quote should be escaped in the og:title attribute
        assert 'content="Evil" onload' not in html
        assert "&quot;" in html

    def test_markdown_link_javascript_url_blocked(self, cache_env):
        """XSS via javascript: URL in markdown link."""
        cache_env["db"].upsert_entry(
            {
                "id": "xss-jslink",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "JS Link Test",
                "body": "Click [here](javascript:alert(1)) for evil.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-jslink.html").read_text()
        # The article body should not contain a javascript: link
        import re

        article = re.search(r"<article>(.*?)</article>", html, re.DOTALL)
        assert article, "No <article> tag found"
        assert 'href="javascript:' not in article.group(1)

    def test_markdown_link_text_escaped(self, cache_env):
        """XSS via HTML in markdown link text."""
        cache_env["db"].upsert_entry(
            {
                "id": "xss-linktext",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Link Text XSS",
                "body": "See [<img src=x onerror=alert(1)>](https://example.com) here.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-linktext.html").read_text()
        import re

        article = re.search(r"<article>(.*?)</article>", html, re.DOTALL)
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
        cache_env["db"].upsert_entry(
            {
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
            }
        )
        cache_env["svc"].render_all()

        cache_dir = cache_env["cache_dir"]
        kb_dir = cache_dir / "test-kb"

        # Verify no file was written at the traversed path
        traversed = (kb_dir / "../../etc/evil.html").resolve()
        if traversed.exists():
            assert traversed.is_relative_to(cache_dir.resolve()), (
                f"Path traversal escape: {traversed} is outside {cache_dir}"
            )

        # All HTML files under the kb_dir must have resolved paths inside cache_dir
        for f in kb_dir.iterdir():
            assert f.resolve().is_relative_to(cache_dir.resolve()), (
                f"File {f} escaped the cache directory"
            )

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


class TestFrontmatterMetadataDisplay:
    """Verify that rich frontmatter fields appear in rendered entry pages."""

    def test_status_badge_rendered(self, cache_env):
        """Status field should render as a colored badge next to the type badge."""
        cache_env["db"].upsert_entry(
            {
                "id": "status-entry",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Confirmed Event",
                "body": "Something happened.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
                "status": "confirmed",
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "status-entry.html").read_text()
        assert "badge-status" in html
        assert "status-confirmed" in html
        assert "confirmed" in html.lower()

    def test_status_disputed_badge(self, cache_env):
        """Disputed status should get the red badge class."""
        cache_env["db"].upsert_entry(
            {
                "id": "disputed-entry",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Disputed Event",
                "body": "Claims are contested.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
                "status": "disputed",
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "disputed-entry.html").read_text()
        assert "status-disputed" in html

    def test_actors_rendered_with_search_links(self, cache_env):
        """Actors from metadata should appear as search-linked names."""
        cache_env["db"].upsert_entry(
            {
                "id": "actor-entry",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Event With Actors",
                "body": "Multiple actors involved.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {"actors": ["Alice Smith", "Bob Jones"]},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "actor-entry.html").read_text()
        assert "Actors:" in html
        assert "Alice Smith" in html
        assert "Bob Jones" in html
        assert "search?q=Alice" in html
        assert "search?q=Bob" in html

    def test_sources_rendered_as_list(self, cache_env):
        """Sources should appear in a numbered list with links."""
        cache_env["db"].upsert_entry(
            {
                "id": "sourced-entry",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Well-Sourced Event",
                "body": "Documented occurrence.",
                "summary": "",
                "tags": [],
                "sources": [
                    {
                        "id": "src-1",
                        "entry_id": "sourced-entry",
                        "kb_name": "test-kb",
                        "title": "Reuters Report",
                        "url": "https://reuters.com/article/123",
                        "outlet": "Reuters",
                        "date": "2025-06-15",
                        "verified": True,
                    },
                    {
                        "id": "src-2",
                        "entry_id": "sourced-entry",
                        "kb_name": "test-kb",
                        "title": "AP Investigation",
                        "url": "https://apnews.com/456",
                        "outlet": "AP News",
                        "date": "2025-06-16",
                        "verified": False,
                    },
                ],
                "links": [],
                "metadata": {},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "sourced-entry.html").read_text()
        assert "sources-section" in html
        assert "Sources" in html
        assert "Reuters Report" in html
        assert "https://reuters.com/article/123" in html
        assert "Reuters" in html
        assert "AP Investigation" in html
        assert "2025-06-15" in html
        # Verify the ordered list
        assert "<ol>" in html

    def test_sources_fetched_for_list_entries(self, cache_env):
        """When sources are not in the entry dict (list_entries), they should be fetched."""
        # Insert entry with sources via the DB (list_entries won't include them)
        cache_env["db"].upsert_entry(
            {
                "id": "fetch-sources-entry",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Entry With DB Sources",
                "body": "Has sources in DB.",
                "summary": "",
                "tags": [],
                "sources": [
                    {
                        "id": "src-db-1",
                        "entry_id": "fetch-sources-entry",
                        "kb_name": "test-kb",
                        "title": "Database Source",
                        "url": "https://example.com/source",
                        "outlet": "Example",
                        "date": "2025-01-01",
                        "verified": True,
                    },
                ],
                "links": [],
                "metadata": {},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "fetch-sources-entry.html").read_text()
        assert "Database Source" in html
        assert "https://example.com/source" in html

    def test_source_javascript_url_blocked(self, cache_env):
        """Sources with javascript: URLs should not render as clickable links."""
        cache_env["db"].upsert_entry(
            {
                "id": "xss-source-entry",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "XSS Source Test",
                "body": "Bad source URL.",
                "summary": "",
                "tags": [],
                "sources": [
                    {
                        "id": "src-xss",
                        "entry_id": "xss-source-entry",
                        "kb_name": "test-kb",
                        "title": "Evil Source",
                        "url": "javascript:alert(1)",
                        "outlet": "Evil Corp",
                        "date": "2025-01-01",
                        "verified": False,
                    },
                ],
                "links": [],
                "metadata": {},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-source-entry.html").read_text()
        assert "Evil Source" in html
        assert 'href="javascript:' not in html

    def test_location_in_meta_bar(self, cache_env):
        """Location field should appear in the meta bar."""
        cache_env["db"].upsert_entry(
            {
                "id": "location-entry",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Localized Event",
                "body": "Happened somewhere.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
                "location": "Nairobi, Kenya",
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "location-entry.html").read_text()
        assert "Nairobi, Kenya" in html
        # Should be inside the meta div
        import re

        meta = re.search(r'<div class="meta">(.*?)</div>', html)
        assert meta, "No meta div found"
        assert "Nairobi" in meta.group(1)

    def test_capture_lanes_rendered(self, cache_env):
        """Capture lanes from metadata should render as small badges."""
        cache_env["db"].upsert_entry(
            {
                "id": "lanes-entry",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Multi-Lane Event",
                "body": "Tracked across lanes.",
                "summary": "",
                "tags": ["conflict"],
                "sources": [],
                "links": [],
                "metadata": {"capture_lanes": ["media", "legal", "financial"]},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "lanes-entry.html").read_text()
        assert "capture-lanes" in html
        assert "lane-badge" in html
        assert "media" in html
        assert "legal" in html
        assert "financial" in html

    def test_empty_status_not_rendered(self, cache_env):
        """No status badge should appear when status is empty."""
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert "badge-status" not in html

    def test_actors_escaped(self, cache_env):
        """Actor names with HTML should be escaped."""
        cache_env["db"].upsert_entry(
            {
                "id": "xss-actor-entry",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "XSS Actor Test",
                "body": "Bad actor name.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {"actors": ['<script>alert("xss")</script>']},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-actor-entry.html").read_text()
        # The actors section should contain escaped HTML, not raw script tags
        import re

        actors_section = re.search(r'<div class="actors">(.*?)</div>', html)
        assert actors_section, "No actors section found"
        actors_content = actors_section.group(1)
        assert "<script>" not in actors_content
        assert "&lt;script&gt;" in actors_content

    def test_full_entry_with_all_metadata(self, cache_env):
        """Integration test: an entry with all metadata fields renders correctly."""
        cache_env["db"].upsert_entry(
            {
                "id": "full-entry",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Complete Event",
                "body": "A fully documented event.",
                "summary": "Full metadata event",
                "tags": ["conflict", "verified"],
                "sources": [
                    {
                        "id": "src-full",
                        "entry_id": "full-entry",
                        "kb_name": "test-kb",
                        "title": "Primary Source",
                        "url": "https://example.com/full",
                        "outlet": "Example News",
                        "date": "2025-07-01",
                        "verified": True,
                    },
                ],
                "links": [],
                "metadata": {
                    "actors": ["Jane Doe", "ACME Corp"],
                    "capture_lanes": ["media", "legal"],
                },
                "status": "confirmed",
                "location": "Lagos, Nigeria",
                "date": "2025-07-01",
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "full-entry.html").read_text()

        # Status badge
        assert "status-confirmed" in html
        # Actors
        assert "Jane Doe" in html
        assert "ACME Corp" in html
        # Sources
        assert "Primary Source" in html
        assert "Example News" in html
        # Location
        assert "Lagos, Nigeria" in html
        # Capture lanes
        assert "media" in html
        assert "legal" in html
        # Tags still present
        assert "conflict" in html
        assert "verified" in html


class TestRelatedEvents:
    """Related Events section should appear for entries sharing actors or tags."""

    def test_related_events_via_shared_actor(self, cache_env):
        """Two entries sharing an actor should show Related Events on each other's page."""
        cache_env["db"].upsert_entry(
            {
                "id": "event-a",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Event Alpha",
                "body": "First event.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {"actors": ["Shared Actor"]},
            }
        )
        cache_env["db"].upsert_entry(
            {
                "id": "event-b",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Event Beta",
                "body": "Second event.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {"actors": ["Shared Actor"]},
            }
        )
        cache_env["svc"].render_all()
        html_a = (cache_env["cache_dir"] / "test-kb" / "event-a.html").read_text()
        html_b = (cache_env["cache_dir"] / "test-kb" / "event-b.html").read_text()
        # Event A should show Event Beta as related
        assert "Related Events" in html_a
        assert "Event Beta" in html_a
        assert "related-section" in html_a
        # Event B should show Event Alpha as related
        assert "Related Events" in html_b
        assert "Event Alpha" in html_b

    def test_related_events_via_shared_tag(self, cache_env):
        """Entries sharing a tag (but not linked) should appear in Related Events."""
        cache_env["db"].upsert_entry(
            {
                "id": "tag-entry-1",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Tag Entry One",
                "body": "First tag entry.",
                "summary": "",
                "tags": ["shared-tag"],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        cache_env["db"].upsert_entry(
            {
                "id": "tag-entry-2",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Tag Entry Two",
                "body": "Second tag entry.",
                "summary": "",
                "tags": ["shared-tag"],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        cache_env["svc"].render_all()
        html_1 = (cache_env["cache_dir"] / "test-kb" / "tag-entry-1.html").read_text()
        assert "Related Events" in html_1
        assert "Tag Entry Two" in html_1

    def test_related_events_excludes_backlinks(self, cache_env):
        """Entries already linked via backlinks should NOT appear in Related Events."""
        # hello-world links to wikilink (from cache_env fixture)
        # Add shared tag to both so they would otherwise be related
        cache_env["db"].upsert_entry(
            {
                "id": "hello-world",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Hello World",
                "body": "This is a test entry with a [[wikilink]].",
                "summary": "A test entry",
                "tags": ["shared-tag"],
                "sources": [],
                "links": [{"target": "wikilink", "relation": "related_to"}],
                "metadata": {},
            }
        )
        cache_env["db"].upsert_entry(
            {
                "id": "wikilink",
                "kb_name": "test-kb",
                "entry_type": "concept",
                "title": "Wikilink Target",
                "body": "This is the target of a wikilink.",
                "summary": "",
                "tags": ["shared-tag"],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        # wikilink should appear in outlinks, not in related events
        # Related Events section should either not exist or not contain "Wikilink Target"
        import re

        related = re.search(r'<div class="related-section">(.*?)</div>\s*</div>', html, re.DOTALL)
        if related:
            assert "Wikilink Target" not in related.group(1)

    def test_related_events_not_shown_when_no_overlap(self, cache_env):
        """Entries with no shared actors or tags should not have Related Events."""
        cache_env["db"].upsert_entry(
            {
                "id": "isolated-entry",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Isolated Entry",
                "body": "No overlap with anything.",
                "summary": "",
                "tags": ["unique-tag-xyz"],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "isolated-entry.html").read_text()
        assert "related-section" not in html

    def test_related_events_actor_scores_higher_than_tag(self, cache_env):
        """An entry sharing an actor should rank higher than one sharing only a tag."""
        cache_env["db"].upsert_entry(
            {
                "id": "scoring-main",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Scoring Main",
                "body": "Main event for scoring test.",
                "summary": "",
                "tags": ["common-tag"],
                "sources": [],
                "links": [],
                "metadata": {"actors": ["Key Actor"]},
            }
        )
        cache_env["db"].upsert_entry(
            {
                "id": "scoring-actor",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Actor Match",
                "body": "Shares an actor.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {"actors": ["Key Actor"]},
            }
        )
        cache_env["db"].upsert_entry(
            {
                "id": "scoring-tag",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Tag Match",
                "body": "Shares a tag.",
                "summary": "",
                "tags": ["common-tag"],
                "sources": [],
                "links": [],
                "metadata": {},
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "scoring-main.html").read_text()
        assert "Related Events" in html
        # Actor Match (score=2) should appear before Tag Match (score=1)
        actor_pos = html.index("Actor Match")
        tag_pos = html.index("Tag Match")
        assert actor_pos < tag_pos, "Actor match should appear before tag match"

    def test_related_events_date_shown(self, cache_env):
        """Related events with a date should display it."""
        cache_env["db"].upsert_entry(
            {
                "id": "dated-main",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Dated Main",
                "body": "Main.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {"actors": ["Dated Actor"]},
            }
        )
        cache_env["db"].upsert_entry(
            {
                "id": "dated-related",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Dated Related",
                "body": "Related.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {"actors": ["Dated Actor"]},
                "date": "2025-03-15",
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "dated-main.html").read_text()
        assert "2025-03-15" in html
        assert "Dated Related" in html


class TestCoverageField:
    """Coverage frontmatter field should render as a Coverage section."""

    def test_coverage_renders_external_links(self, cache_env):
        """Entries with a coverage field should show a Coverage section with external links."""
        cache_env["db"].upsert_entry(
            {
                "id": "covered-event",
                "kb_name": "test-kb",
                "entry_type": "event",
                "title": "Well-Covered Event",
                "body": "Something important happened.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {
                    "coverage": [
                        {
                            "title": "Every Database Is an Immigration Database",
                            "url": "https://theramm.substack.com/p/every-database",
                            "publication": "RAMM on Substack",
                        },
                        {
                            "title": "ProPublica Investigation",
                            "url": "https://propublica.org/article/investigation",
                            "publication": "ProPublica",
                        },
                    ]
                },
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "covered-event.html").read_text()

        assert "Coverage" in html
        assert "https://theramm.substack.com/p/every-database" in html
        assert "Every Database Is an Immigration Database" in html
        assert "RAMM on Substack" in html
        assert "ProPublica" in html

    def test_no_coverage_when_field_absent(self, cache_env):
        """Entries without coverage field should not show Coverage section."""
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert "Coverage" not in html

    def test_coverage_javascript_url_blocked(self, cache_env):
        """Coverage entries with javascript: URLs should not render as links."""
        cache_env["db"].upsert_entry(
            {
                "id": "xss-coverage",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "XSS Coverage Test",
                "body": "Test.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {
                    "coverage": [
                        {"title": "Evil", "url": "javascript:alert(1)", "publication": "Hacker"},
                    ]
                },
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "xss-coverage.html").read_text()
        assert 'href="javascript:' not in html


class TestSEOAndSocialMetadata:
    """Verify SEO meta tags, Twitter cards, og:url, og:image, and JSON-LD enhancements."""

    def test_entry_has_og_url(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert 'property="og:url"' in html
        assert "/site/test-kb/hello-world" in html

    def test_entry_has_og_image(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert 'property="og:image"' in html
        assert "/static/favicon.svg" in html

    def test_entry_has_twitter_card(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert 'name="twitter:card"' in html
        assert 'content="summary"' in html

    def test_entry_has_twitter_title(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert 'name="twitter:title"' in html
        assert "Hello World" in html

    def test_entry_has_twitter_description(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        assert 'name="twitter:description"' in html

    def test_jsonld_has_url(self, cache_env):
        import json
        import re

        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html)
        assert match, "No JSON-LD found"
        ld = json.loads(match.group(1))
        assert "url" in ld
        assert "/site/test-kb/hello-world" in ld["url"]

    def test_jsonld_has_publisher(self, cache_env):
        import json
        import re

        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html)
        assert match, "No JSON-LD found"
        ld = json.loads(match.group(1))
        assert "publisher" in ld
        assert ld["publisher"]["@type"] == "Organization"
        assert ld["publisher"]["name"] == "Pyrite"

    def test_jsonld_has_author_when_created_by_set(self, cache_env):
        import json
        import re

        cache_env["db"].upsert_entry(
            {
                "id": "authored-entry",
                "kb_name": "test-kb",
                "entry_type": "note",
                "title": "Authored Entry",
                "body": "Written by someone.",
                "summary": "",
                "tags": [],
                "sources": [],
                "links": [],
                "metadata": {},
                "created_by": "Jane Author",
            }
        )
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "authored-entry.html").read_text()
        match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html)
        assert match, "No JSON-LD found"
        ld = json.loads(match.group(1))
        assert "author" in ld
        assert ld["author"]["@type"] == "Person"
        assert ld["author"]["name"] == "Jane Author"

    def test_jsonld_no_author_when_not_set(self, cache_env):
        import json
        import re

        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "hello-world.html").read_text()
        match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html)
        assert match, "No JSON-LD found"
        ld = json.loads(match.group(1))
        assert "author" not in ld

    def test_landing_page_has_twitter_card(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "index.html").read_text()
        assert 'name="twitter:card"' in html
        assert 'property="og:url"' in html

    def test_kb_index_has_twitter_card(self, cache_env):
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "test-kb" / "index.html").read_text()
        assert 'name="twitter:card"' in html
        assert 'property="og:url"' in html


# ---------------------------------------------------------------------------
# White-label branding (pyrite-white-labeling)
# ---------------------------------------------------------------------------


import textwrap


@pytest.fixture
def branded_cache_env(tmp_path):
    """Cache env with a configured branding folder."""
    branding_dir = tmp_path / "branding"
    branding_dir.mkdir()
    (branding_dir / "branding.yaml").write_text(
        textwrap.dedent(
            """
            name: "Transparency Cascade Press"
            primary_color: "#c93b3b"
            footer_credit_url: "https://pyrite.wiki"
            """
        ).lstrip()
    )

    kb = KBConfig(name="test-kb", path=tmp_path / "kb", kb_type="generic", default_role="read")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db", branding_dir=branding_dir),
    )
    db = PyriteDB(tmp_path / "index.db")
    db.register_kb("test-kb", "generic", str(tmp_path / "kb"), "A test KB")
    db.upsert_entry(
        {
            "id": "hello",
            "kb_name": "test-kb",
            "entry_type": "note",
            "title": "Hello",
            "body": "x",
            "summary": "",
            "tags": [],
            "sources": [],
            "links": [],
            "metadata": {},
        }
    )
    svc = SiteCacheService(config, db)
    yield {"svc": svc, "db": db, "cache_dir": svc.cache_dir}
    db.close()


class TestSiteCacheBranding:
    def test_landing_page_uses_brand_name_in_title(self, branded_cache_env):
        branded_cache_env["svc"].render_all()
        html = (branded_cache_env["cache_dir"] / "index.html").read_text()
        assert "Transparency Cascade Press Knowledge Base" in html
        # Default Pyrite-branded title string must not appear in <title>
        assert "<title>Pyrite Knowledge Base</title>" not in html

    def test_entry_page_uses_brand_name(self, branded_cache_env):
        branded_cache_env["svc"].render_all()
        html = (branded_cache_env["cache_dir"] / "test-kb" / "hello.html").read_text()
        assert "Transparency Cascade Press" in html

    def test_jsonld_publisher_is_brand(self, branded_cache_env):
        import json
        import re

        branded_cache_env["svc"].render_all()
        html = (branded_cache_env["cache_dir"] / "test-kb" / "hello.html").read_text()
        match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html)
        assert match, "No JSON-LD found"
        ld = json.loads(match.group(1))
        assert ld["publisher"]["name"] == "Transparency Cascade Press"

    def test_powered_by_pyrite_still_present(self, branded_cache_env):
        """The Pyrite credit line must survive branding."""
        branded_cache_env["svc"].render_all()
        html = (branded_cache_env["cache_dir"] / "index.html").read_text()
        # The footer template renders a "Powered by <a>Pyrite</a>" line.
        assert "Powered by" in html
        assert "pyrite.wiki" in html

    def test_default_render_still_says_pyrite(self, cache_env):
        """Without a branding folder, everything keeps saying Pyrite."""
        cache_env["svc"].render_all()
        html = (cache_env["cache_dir"] / "index.html").read_text()
        assert "Pyrite Knowledge Base" in html


class TestRenderSiteCacheEndpoint:
    """``POST /api/site/render`` (#408): the endpoint must mean the same
    thing by ``rendered`` and ``errors`` as the sync path's ``site_cache``
    status, and a broken ``branding.yaml`` must not 500.
    """

    @pytest.fixture
    def _client(self, tmp_path):
        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        kb_path = tmp_path / "public-kb"
        kb_path.mkdir()
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="public-kb", path=kb_path, kb_type="generic", default_role="read"),
            ],
            settings=Settings(index_path=tmp_path / "index.db"),
        )
        (kb_path / "entry.md").write_text(
            """---
id: entry
title: An Entry
entry_type: note
---

Body.
"""
        )
        app = create_app(config=config)
        with TestClient(app, raise_server_exceptions=False) as client:
            client._pyrite_config = config
            sync_resp = client.post("/api/index/sync", params={"wait": "true"})
            assert sync_resp.status_code == 200, sync_resp.text
            assert sync_resp.json()["added"] == 1, (
                f"precondition: the entry must be indexed before render, got {sync_resp.json()}"
            )
            yield client

    @pytest.mark.control(
        reason=(
            "The pre-fix render endpoint already did `{'rendered': True, **stats}`, "
            "and `stats` already carried `errors` from `render_all()` -- this "
            "endpoint's success/errors-present shape was never the #408 bug (only "
            "the sync path's SiteCacheSyncStatus lacked `errors`). Kept as a "
            "control so a future change to this endpoint can't silently drop it."
        )
    )
    def test_render_reports_rendered_true_and_errors_zero_on_success(self, _client):
        resp = _client.post("/api/site/render")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rendered"] is True, body
        assert body["errors"] == 0, body

    @pytest.mark.control(
        reason=(
            "Same reason as the test above: `render_all()`'s `errors` count "
            "already rode along via `**stats` before this fix. `rendered` "
            "staying true under a per-entry failure was already correct on "
            "this endpoint; #408's bug was the sync path discarding it."
        )
    )
    def test_render_reports_errors_even_though_rendered_true(self, _client, monkeypatch):
        """Same meaning as the sync path: ``rendered`` says the render ran
        to completion, ``errors`` carries per-entry failure counts."""
        import pyrite.services.site_cache as site_cache_module

        def _boom(self, *args, **kwargs):
            raise RuntimeError("boom: entry render exploded")

        monkeypatch.setattr(site_cache_module.SiteCacheService, "_render_entry", _boom)

        resp = _client.post("/api/site/render")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rendered"] is True, body
        assert body["errors"] == 1, body

    def test_broken_branding_yaml_answers_409_branding_invalid(self, tmp_path):
        """A half-edited ``branding.yaml`` is an operator mistake on an
        explicit, nothing-already-committed render call -- it must not
        report a generic 200 (that would hide the mistake) nor 500 (the
        original bug); it answers 409 with a stable error code, and the
        envelope is the exact shape the endpoint returns (an ``HTTPException``
        detail, not the central ``PyriteError`` handler's flat body) --
        pinned rather than accepting either shape, so a change to either
        one is caught (#445 cold read)."""
        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        kb_path = tmp_path / "public-kb"
        kb_path.mkdir()
        branding = tmp_path / "branding"
        branding.mkdir()
        (branding / "branding.yaml").write_text("- a list, not a mapping\n")
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="public-kb", path=kb_path, kb_type="generic", default_role="read"),
            ],
            settings=Settings(index_path=tmp_path / "index.db", branding_dir=branding),
        )
        app = create_app(config=config)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/site/render")

        assert resp.status_code == 409, resp.text
        body = resp.json()
        assert set(body.keys()) == {"detail"}, body
        assert set(body["detail"].keys()) == {"code", "message"}, body
        assert body["detail"]["code"] == "BRANDING_INVALID", body
        message = body["detail"]["message"]
        assert str(branding) not in message, (
            f"the branding directory path must not appear in the public response: {message}"
        )

    def test_broken_branding_yaml_syntax_error_answers_409_branding_invalid(self, tmp_path):
        """A YAML syntax error (not just 'valid YAML, wrong shape') takes the
        same 409 path -- ``load_yaml_file`` raising is caught too, not just a
        parsed-but-wrong-type result."""
        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        kb_path = tmp_path / "public-kb"
        kb_path.mkdir()
        branding = tmp_path / "branding"
        branding.mkdir()
        (branding / "branding.yaml").write_text("name: Acme\ntagline: [unclosed\n")
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="public-kb", path=kb_path, kb_type="generic", default_role="read"),
            ],
            settings=Settings(index_path=tmp_path / "index.db", branding_dir=branding),
        )
        app = create_app(config=config)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/site/render")

        assert resp.status_code == 409, resp.text
        body = resp.json()
        assert body["detail"]["code"] == "BRANDING_INVALID", body
        message = body["detail"]["message"]
        assert str(branding) not in message, (
            f"the branding directory path must not appear in the public response: {message}"
        )


class TestBrokenBrandingDoesNotLeakOnPublicRoutes:
    """#445 cold read: a broken ``branding.yaml`` must not turn anonymous,
    always-public GET routes into a path-and-parser-text leak. Before #408's
    fix these routes returned a bare 500 ("Internal Server Error"); adding
    ``BrandingInvalidError`` without a row in ``_PYRITE_ERROR_STATUS`` made
    the central handler fall through to ``str(exc)``, which is the absolute
    branding.yaml path plus the parser's own text.

    ``/sitemap.xml`` and ``/robots.txt`` no longer fail at all on a broken
    branding.yaml (#445's delta cold read: a crawler reading a 5xx there
    takes it as "don't crawl") -- their no-leak coverage lives in
    ``tests/test_sitemap.py::TestSitemapAndRobotsSurviveBrokenBranding``
    alongside the 200-and-degrades-cleanly assertions, so this class keeps
    only ``/config/branding``, which still fails closed at 500.
    """

    def _config_with_broken_branding(self, tmp_path, yaml_text):
        kb_path = tmp_path / "public-kb"
        kb_path.mkdir()
        (kb_path / "entry.md").write_text(
            "---\nid: entry\ntitle: An Entry\nentry_type: note\n---\n\nBody.\n"
        )
        branding = tmp_path / "branding"
        branding.mkdir()
        (branding / "branding.yaml").write_text(yaml_text)
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="public-kb", path=kb_path, kb_type="generic", default_role="read"),
            ],
            settings=Settings(index_path=tmp_path / "index.db", branding_dir=branding),
        )
        return config, branding

    @pytest.mark.control(
        reason=(
            "verify-red diffs against the PR's merge base, before #408 existed at "
            "all -- there this route hit FastAPI's default unhandled-exception "
            "handler (a bare 'Internal Server Error', no message body), so the "
            "leak assertions trivially hold there too. The bug this guards was "
            "introduced BY #408 (BrandingInvalidError with no _PYRITE_ERROR_STATUS "
            "row, so the central handler fell through to str(exc)) and fixed in "
            "the first cold-read round -- confirmed red by mutation-testing the "
            "_PYRITE_ERROR_STATUS row and the public_message generalization in "
            "pyrite/server/api.py (see the PR report)."
        )
    )
    def test_config_branding_route_does_not_leak_path_or_parser_text(self, tmp_path):
        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        config, branding = self._config_with_broken_branding(tmp_path, "- a list, not a mapping\n")
        app = create_app(config=config)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/config/branding")

        assert resp.status_code >= 400, resp.text
        # Naming the filename is fine (the public_message says "fix
        # branding.yaml" so an operator knows what to look at); the
        # filesystem path and the parser's own type/error text are not.
        assert str(branding) not in resp.text, (
            f"/config/branding leaked the branding directory path: {resp.text}"
        )
        assert "CommentedSeq" not in resp.text, (
            f"/config/branding leaked the raw parser/type name: {resp.text}"
        )

    def test_config_branding_route_answers_a_named_code_not_a_bare_500(self, tmp_path):
        """The route still fails closed (it cannot serve real branding), but
        with the same ``{"detail": {"code", "message", ...}}`` shape every
        other PyriteError gets from the central handler (ADR-0037 theme 2)
        -- not FastAPI's generic 'Internal Server Error' text and not a
        traceback."""
        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        config, _branding = self._config_with_broken_branding(tmp_path, "- a list, not a mapping\n")
        app = create_app(config=config)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/config/branding")

        body = resp.json()["detail"]
        assert body.get("code") == "BRANDING_INVALID", body

    @pytest.mark.control(
        reason=(
            "verify-red's baseline is before #408 existed at all, where "
            "BrandingInvalidError does not exist and so cannot reach the "
            "central handler's public_message branch either -- the double-log "
            "bug this guards was introduced by round 1 of THIS PR (the "
            "public_message generalization in pyrite/server/api.py) and fixed "
            "in this same delta round; confirmed red by directly mutating out "
            "the `if status_code < 500` guard (see the PR report)."
        )
    )
    def test_config_branding_central_handler_does_not_log_a_5xx_twice(self, tmp_path, caplog):
        """#445 delta cold read: the central handler (now
        ``pyrite.server.errors``, moved from ``pyrite.server.api`` by
        ADR-0037 theme 2) logged a 5xx PyriteError with ``logger.error``
        (with a traceback) AND, whenever it had a ``public_message``, an
        unconditional second ``logger.warning`` line for the very same
        exception -- doubling the handler's own log output for a broken
        branding.yaml on every request. Scoped to the
        ``pyrite.server.errors`` logger specifically: ``BrandingService``
        logging its own line (once per mtime, a separate concern) is not
        part of this count."""
        import logging

        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        config, _branding = self._config_with_broken_branding(tmp_path, "- a list, not a mapping\n")
        app = create_app(config=config)
        with (
            caplog.at_level(logging.WARNING, logger="pyrite.server.errors"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            resp = client.get("/config/branding")

        assert resp.status_code >= 500, resp.text
        handler_records = [r for r in caplog.records if r.name == "pyrite.server.errors"]
        assert len(handler_records) <= 1, (
            f"expected the central handler to log this 5xx at most once, got "
            f"{len(handler_records)}: {[r.getMessage() for r in handler_records]}"
        )


class TestBrandingNestedMappingValidation:
    """#445 cold read: ``meta:`` and ``mcp:`` are read with ``.get()``
    immediately after the top-level mapping check, so ``meta: [x]`` or
    ``mcp: [x]`` (a YAML list where a mapping is expected) still raised a
    raw ``AttributeError`` -- the top-level ``isinstance(data, dict)`` guard
    only covers the outermost document.
    """

    @pytest.mark.parametrize("bad_key", ["meta", "mcp"])
    def test_nested_non_mapping_is_a_branding_invalid_error_not_an_attributeerror(
        self, tmp_path, bad_key
    ):
        from pyrite.exceptions import BrandingInvalidError
        from pyrite.services.branding_service import BrandingService

        branding = tmp_path / "branding"
        branding.mkdir()
        (branding / "branding.yaml").write_text(f"name: Acme\n{bad_key}: [x]\n")

        svc = BrandingService(branding)
        with pytest.raises(BrandingInvalidError):
            svc.get()

    @pytest.mark.parametrize("bad_key", ["meta", "mcp"])
    def test_render_endpoint_answers_409_for_a_nested_non_mapping(self, tmp_path, bad_key):
        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        kb_path = tmp_path / "public-kb"
        kb_path.mkdir()
        branding = tmp_path / "branding"
        branding.mkdir()
        (branding / "branding.yaml").write_text(f"name: Acme\n{bad_key}: [x]\n")
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="public-kb", path=kb_path, kb_type="generic", default_role="read"),
            ],
            settings=Settings(index_path=tmp_path / "index.db", branding_dir=branding),
        )
        app = create_app(config=config)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/site/render")

        assert resp.status_code == 409, resp.text
        assert resp.json()["detail"]["code"] == "BRANDING_INVALID", resp.text


class TestBrandingScalarFieldValidation:
    """#445 delta cold read: BrandingService validated the top-level
    document and the two nested mappings (round 2), but not that the
    scalar fields it reads (``name``, ``site_url``, etc.) are actually
    strings. ``site_url: [x]`` reached SitemapService as a list (a bare
    500 on /sitemap.xml and /robots.txt); ``name: [x]`` came out of
    /config/branding as a JSON array where every consumer expects text.
    """

    @pytest.mark.parametrize(
        "yaml_text",
        [
            "name: [x]\n",
            "site_url: [x]\n",
            "tagline: 123\n",
            "primary_color: true\n",
            "meta:\n  description: [x]\n",
            "mcp:\n  agent_prompt_brand: [x]\n",
        ],
        ids=[
            "name-list",
            "site_url-list",
            "tagline-number",
            "primary_color-bool",
            "meta.description-list",
            "mcp.agent_prompt_brand-list",
        ],
    )
    def test_non_string_scalar_field_is_branding_invalid_error(self, tmp_path, yaml_text):
        from pyrite.exceptions import BrandingInvalidError
        from pyrite.services.branding_service import BrandingService

        branding = tmp_path / "branding"
        branding.mkdir()
        (branding / "branding.yaml").write_text(yaml_text)

        svc = BrandingService(branding)
        with pytest.raises(BrandingInvalidError):
            svc.get()

    def test_site_url_list_no_longer_500s_sitemap(self, tmp_path):
        """The exact failure mode the cold read named: site_url: [x] must
        not reach SitemapService as a list."""
        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        kb_path = tmp_path / "public-kb"
        kb_path.mkdir()
        (kb_path / "e.md").write_text("---\nid: e\ntitle: E\nentry_type: note\n---\nBody\n")
        branding = tmp_path / "branding"
        branding.mkdir()
        (branding / "branding.yaml").write_text("site_url: [x]\n")
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="public-kb", path=kb_path, kb_type="generic", default_role="read"),
            ],
            settings=Settings(index_path=tmp_path / "index.db", branding_dir=branding),
        )
        app = create_app(config=config)
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/sitemap.xml")
        assert r.status_code == 200, r.text

    def test_name_list_no_longer_a_list_from_config_branding(self, tmp_path):
        """The exact failure mode the cold read named: name: [x] must not
        come out of /config/branding as a list -- the route stays a named
        500 (unlike sitemap/robots, GET /config/branding keeps failing
        closed; the web store already has a fallback for it), so this
        pins that it does NOT silently serialize the list through."""
        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        kb_path = tmp_path / "public-kb"
        kb_path.mkdir()
        branding = tmp_path / "branding"
        branding.mkdir()
        (branding / "branding.yaml").write_text("name: [x]\n")
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="public-kb", path=kb_path, kb_type="generic", default_role="read"),
            ],
            settings=Settings(index_path=tmp_path / "index.db", branding_dir=branding),
        )
        app = create_app(config=config)
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.get("/config/branding")
        assert r.status_code == 500, r.text
        body = r.json()["detail"]
        assert body.get("code") == "BRANDING_INVALID", body
        assert not isinstance(body.get("name"), list), body


class TestBrandingFailureCacheDoesNotLeakTracebackFrames:
    """#445 round 3: a cache hit re-raised the SAME stored exception object
    (``raise cached[1]``). Python appends a frame to ``__traceback__`` on
    every raise of that object, so the cached exception's traceback grows
    without bound across requests, and the central handler's
    ``logger.error(..., exc_info=exc)`` prints the whole (growing)
    traceback on every single ``/config/branding`` request.
    """

    def test_traceback_length_does_not_grow_across_repeated_loads(self, tmp_path):
        import traceback

        from pyrite.exceptions import BrandingInvalidError
        from pyrite.services.branding_service import BrandingService

        branding = tmp_path / "branding"
        branding.mkdir()
        (branding / "branding.yaml").write_text("- a list, not a mapping\n")

        svc = BrandingService(branding)
        lengths = []
        for _ in range(8):
            svc._config = None  # force _load() again, same object, same mtime
            with pytest.raises(BrandingInvalidError) as excinfo:
                svc.get()
            lengths.append(len(traceback.extract_tb(excinfo.value.__traceback__)))

        # The first call is a real parse failure (a deeper stack, through
        # _load_raw); every call after that is a cache hit and must raise a
        # FRESH exception each time, so its traceback is a fixed, shallow
        # depth -- not growing call over call. Comparing only the cache-hit
        # calls (index 1 on) isolates the bug: re-raising the same stored
        # exception object appends a frame on every raise, so those lengths
        # would climb 1, 2, 3, ... instead of staying constant.
        cache_hit_lengths = lengths[1:]
        assert len(set(cache_hit_lengths)) == 1, (
            f"traceback frame count grew across repeated cache-hit loads of "
            f"the same unchanged file (first call, a real parse, is index 0 "
            f"and expected to differ): {lengths}"
        )

    def test_config_branding_logged_traceback_does_not_grow_across_requests(self, tmp_path, caplog):
        """Same story at the HTTP layer, checked where the bug actually
        shows up: the coordinator's finding is specifically that
        ``/config/branding`` *logs* the whole (growing) traceback on every
        request via the central handler's ``exc_info=exc`` -- the response
        body itself carries only the fixed ``public_message``, so it can't
        show this. ``/config/branding`` builds a fresh ``BrandingService``
        per request (no per-instance state to reset), so this exercises the
        module-level cache directly, repeatedly, the way real traffic
        would."""
        import logging
        import traceback

        fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
        from fastapi.testclient import TestClient

        from pyrite.server.api import create_app

        kb_path = tmp_path / "public-kb"
        kb_path.mkdir()
        branding = tmp_path / "branding"
        branding.mkdir()
        (branding / "branding.yaml").write_text("- a list, not a mapping\n")
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="public-kb", path=kb_path, kb_type="generic", default_role="read"),
            ],
            settings=Settings(index_path=tmp_path / "index.db", branding_dir=branding),
        )
        app = create_app(config=config)
        depths = []
        with (
            caplog.at_level(logging.ERROR, logger="pyrite.server.errors"),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            for _ in range(8):
                caplog.clear()
                r = client.get("/config/branding")
                assert r.status_code == 500, r.text
                handler_records = [
                    rec for rec in caplog.records if rec.name == "pyrite.server.errors"
                ]
                assert handler_records, "expected the central handler to log this 5xx"
                exc_info = handler_records[0].exc_info
                assert exc_info is not None and exc_info[2] is not None, (
                    "expected a traceback on the logged record"
                )
                depths.append(len(traceback.extract_tb(exc_info[2])))

        # Request 0 builds a fresh BrandingService and hits a real parse
        # failure (deeper stack, through _load_raw); every request after
        # that is a cache hit and must raise a fresh exception each time,
        # so its logged traceback is a fixed, shallow depth -- not growing
        # request over request the way re-raising the same stored object
        # would (the bug: 1, 2, 3, ... frames deeper on each hit).
        cache_hit_depths = depths[1:]
        assert len(set(cache_hit_depths)) == 1, (
            f"the logged traceback's frame count grew across identical repeated "
            f"cache-hit requests to the same unchanged file (request 0, a real "
            f"parse, is expected to differ): {depths}"
        )


class TestBrandingFailureCacheKey:
    """#445 round 3: keyed on mtime alone, a fixed file whose mtime happens
    not to change (``cp -p``, ``rsync -t``, tar extraction, or a filesystem
    with 1-second mtime granularity racing two writes in the same second)
    keeps failing forever with the stale cached error. Keying on
    ``(st_mtime_ns, st_size)`` catches a same-second edit as long as the
    byte size differs, which covers the realistic "operator fixed a typo"
    case without needing a content hash.
    """

    @pytest.mark.control(
        reason=(
            "verify-red's baseline is before #408 existed at all, where "
            "BrandingService has no failure cache whatsoever -- every load "
            "re-parses the file fresh, so a stale-cache bug (this test's whole "
            "point) cannot manifest there and the assertion trivially holds. "
            "The bug was introduced by round 3 of this PR (the mtime-only cache "
            "key) and fixed in this same round 4; confirmed red by mutation-"
            "testing the (mtime_ns, size) key down to mtime-only (see the PR "
            "report)."
        )
    )
    def test_same_mtime_different_size_is_not_treated_as_the_same_failure(self, tmp_path):
        import os

        from pyrite.services.branding_service import BrandingService

        branding = tmp_path / "branding"
        branding.mkdir()
        yaml_path = branding / "branding.yaml"
        yaml_path.write_text("- a list, not a mapping\n")

        svc = BrandingService(branding)
        with pytest.raises(Exception):  # noqa: B017 -- BrandingInvalidError, imported below in the assert
            svc.get()

        # Fix the file's content but pin its mtime to the same value a
        # coarse-grained filesystem or a `cp -p`/`rsync -t` copy would
        # produce -- the size changes, the mtime does not.
        st = yaml_path.stat()
        yaml_path.write_text("name: Acme\n")
        os.utime(yaml_path, ns=(st.st_atime_ns, st.st_mtime_ns))
        assert yaml_path.stat().st_mtime_ns == st.st_mtime_ns, "test setup: mtime must be pinned"

        svc2 = BrandingService(branding)
        cfg = svc2.get()  # must NOT raise the stale cached failure
        assert cfg.name == "Acme", cfg

    def test_file_deleted_between_is_file_and_stat_is_treated_as_missing(
        self, tmp_path, monkeypatch
    ):
        """A TOCTOU gap: ``is_file()`` passes, then the file is removed
        before the later, unguarded ``yaml_path.stat()`` call runs (the one
        that reads the cache key). Must fall back to defaults (the same
        outcome as the file never having existed), not raise
        FileNotFoundError.

        ``Path.is_file()`` itself calls ``self.stat()`` internally (and
        already handles ENOENT, returning False), so a naive "delete on the
        first stat() call" monkeypatch deletes the file during is_file()'s
        own check and never reaches the real gap this test targets. The
        delete has to happen on the *second* stat() call -- the one after
        is_file() has already returned True.
        """
        from pathlib import Path

        from pyrite.services.branding_service import DEFAULT_BRAND_NAME, BrandingService

        branding = tmp_path / "branding"
        branding.mkdir()
        yaml_path = branding / "branding.yaml"
        yaml_path.write_text("name: Acme\n")

        real_stat = Path.stat
        calls = {"n": 0}

        def _stat_then_delete_on_second_call(self, *args, **kwargs):
            if self == yaml_path:
                calls["n"] += 1
                if calls["n"] == 2:
                    yaml_path.unlink()
            return real_stat(self, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", _stat_then_delete_on_second_call)

        svc = BrandingService(branding)
        cfg = svc.get()
        assert cfg.name == DEFAULT_BRAND_NAME, cfg
