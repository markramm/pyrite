"""Web Clipper service — fetch URL, extract content, convert to Markdown."""

import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ClipResult:
    """Result of clipping a URL."""

    title: str
    body: str
    source_url: str
    description: str = ""


class _TitleExtractor(HTMLParser):
    """Minimal HTML parser to extract <title> text."""

    def __init__(self):
        super().__init__()
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def _extract_title(html: str) -> str:
    """Extract <title> from HTML."""
    parser = _TitleExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.title.strip()


def _extract_description(html: str) -> str:
    """Extract meta description from HTML."""
    match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        html,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    # Try og:description
    match = re.search(
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
        html,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def _strip_elements(html: str) -> str:
    """Remove script, style, nav, footer, header, and aside elements."""
    for tag in ("script", "style", "nav", "footer", "header", "aside", "noscript"):
        html = re.sub(
            rf"<{tag}[^>]*>.*?</{tag}>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
    return html


class ClipperService:
    """Fetches URLs and converts HTML to Markdown entries."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def clip_url(self, url: str, title: str | None = None) -> ClipResult:
        """Fetch a URL and convert to Markdown.

        Args:
            url: The URL to clip.
            title: Optional override title.

        Returns:
            ClipResult with title, body (Markdown), source_url, description.
        """
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "Pyrite-Clipper/1.0"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        html = response.text

        # Extract metadata before stripping
        extracted_title = title or _extract_title(html) or url
        description = _extract_description(html)

        # Strip non-content elements
        cleaned = _strip_elements(html)

        # Convert to Markdown
        try:
            from markdownify import markdownify

            body = markdownify(cleaned, heading_style="ATX", strip=["img"])
        except ImportError:
            # Fallback: strip all HTML tags
            body = re.sub(r"<[^>]+>", "", cleaned)

        # Clean up excessive whitespace
        body = re.sub(r"\n{3,}", "\n\n", body).strip()

        return ClipResult(
            title=extracted_title,
            body=body,
            source_url=url,
            description=description,
        )
