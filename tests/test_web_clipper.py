"""Tests for Web Clipper feature."""

import pytest


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


class TestClipUrl:
    """Test full clip_url with mocked HTTP."""

    def test_clip_url_fetches_and_converts(self):
        """clip_url fetches HTML, extracts title and body as Markdown."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        from pyrite.services.clipper import ClipperService

        html = """<html>
        <head><title>Test Article</title>
        <meta name="description" content="A test article about testing.">
        </head>
        <body>
        <nav>Menu</nav>
        <main>
        <h1>Test Article</h1>
        <p>This is the article content with <strong>bold text</strong>.</p>
        </main>
        <footer>Footer</footer>
        </body>
        </html>"""

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("pyrite.services.clipper.httpx.AsyncClient", return_value=mock_client):
            svc = ClipperService()
            result = asyncio.run(svc.clip_url("https://example.com/article"))

        assert result.title == "Test Article"
        assert result.source_url == "https://example.com/article"
        assert result.description == "A test article about testing."
        assert "article content" in result.body
        assert "<nav" not in result.body
        assert "<footer" not in result.body

    def test_clip_url_with_title_override(self):
        """clip_url uses provided title instead of HTML title."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        from pyrite.services.clipper import ClipperService

        html = "<html><head><title>Original</title></head><body><p>Content</p></body></html>"

        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("pyrite.services.clipper.httpx.AsyncClient", return_value=mock_client):
            svc = ClipperService()
            result = asyncio.run(svc.clip_url("https://example.com", title="Custom Title"))

        assert result.title == "Custom Title"

    def test_clip_url_http_error(self):
        """clip_url raises on HTTP error."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        import httpx

        from pyrite.services.clipper import ClipperService

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("pyrite.services.clipper.httpx.AsyncClient", return_value=mock_client):
            svc = ClipperService()
            with pytest.raises(httpx.HTTPStatusError):
                asyncio.run(svc.clip_url("https://example.com/404"))
