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
        assert "application/ld+json" in html

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
        kb = KBConfig(name="public-kb", path=tmp_path / "kb", kb_type="generic", read_only=True)
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
        kb = KBConfig(name="my-kb", path=tmp_path / "kb", kb_type="generic")
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
        kb = KBConfig(name="my-kb", path=tmp_path / "kb", kb_type="generic")
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

    kb = KBConfig(name="test-kb", path=tmp_path / "kb", kb_type="generic")
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
