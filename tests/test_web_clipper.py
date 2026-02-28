"""Tests for Web Clipper feature."""


class TestClipperSchemas:
    """Test clipper request/response schemas."""

    def test_clip_request_schema(self):
        """ClipRequest has required fields."""
        from pyrite.server.schemas import ClipRequest

        req = ClipRequest(url="https://example.com", kb="test-kb")
        assert req.url == "https://example.com"
        assert req.kb == "test-kb"
        assert req.title is None
        assert req.tags == []
        assert req.entry_type == "note"

    def test_clip_request_with_options(self):
        """ClipRequest with optional fields."""
        from pyrite.server.schemas import ClipRequest

        req = ClipRequest(
            url="https://example.com",
            kb="test-kb",
            title="Custom Title",
            tags=["web", "research"],
            entry_type="document",
        )
        assert req.title == "Custom Title"
        assert req.tags == ["web", "research"]
        assert req.entry_type == "document"

    def test_clip_response_schema(self):
        """ClipResponse has expected fields."""
        from pyrite.server.schemas import ClipResponse

        resp = ClipResponse(
            created=True,
            id="example-com",
            kb_name="test-kb",
            title="Example",
            source_url="https://example.com",
        )
        assert resp.created is True
        assert resp.id == "example-com"
        assert resp.source_url == "https://example.com"


class TestClipperEndpoint:
    """Test clipper endpoint registration."""

    def test_clipper_endpoint_exists(self):
        """Clipper router is registered in the app."""
        from pyrite.server.api import create_app

        app = create_app()
        route_paths = [r.path for r in app.routes]
        assert "/api/clip" in route_paths


class TestClipperService:
    """Test ClipperService HTML processing."""

    def test_clipper_service_extracts_title(self):
        """Title extracted from HTML."""
        from pyrite.services.clipper import _extract_title

        html = "<html><head><title>My Page</title></head><body></body></html>"
        assert _extract_title(html) == "My Page"

    def test_clipper_service_extracts_title_empty(self):
        """Empty title returns empty string."""
        from pyrite.services.clipper import _extract_title

        assert _extract_title("<html><body>no title</body></html>") == ""

    def test_clipper_service_strips_scripts(self):
        """Script tags are removed."""
        from pyrite.services.clipper import _strip_elements

        html = '<p>Hello</p><script>alert("x")</script><p>World</p>'
        cleaned = _strip_elements(html)
        assert "<script" not in cleaned
        assert "Hello" in cleaned
        assert "World" in cleaned

    def test_clipper_service_strips_nav(self):
        """Nav, footer, header elements are removed."""
        from pyrite.services.clipper import _strip_elements

        html = "<nav>menu</nav><main><p>Content</p></main><footer>foot</footer>"
        cleaned = _strip_elements(html)
        assert "<nav" not in cleaned
        assert "<footer" not in cleaned
        assert "Content" in cleaned

    def test_clipper_service_extracts_description(self):
        """Meta description extracted."""
        from pyrite.services.clipper import _extract_description

        html = '<meta name="description" content="A great article">'
        assert _extract_description(html) == "A great article"

    def test_clipper_service_extracts_og_description(self):
        """OG description fallback."""
        from pyrite.services.clipper import _extract_description

        html = '<meta property="og:description" content="OG desc">'
        assert _extract_description(html) == "OG desc"
