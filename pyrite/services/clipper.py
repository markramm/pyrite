"""Web Clipper service — fetch URL, extract content, convert to Markdown."""

import ipaddress
import logging
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from ..exceptions import ClipperBlockedHostError

logger = logging.getLogger(__name__)


def _check_url_safe(url: str) -> None:
    """Reject URLs that would let the clipper act as an SSRF gadget.

    Raises ClipperBlockedHostError if:
      - the scheme is not http(s);
      - the URL has no host;
      - the host resolves to a loopback, link-local, private, reserved,
        unspecified, or multicast IPv4/IPv6 address.

    All resolved IPs for the host are checked. If ANY resolved IP is
    blocked, the URL is rejected — that prevents the trivial DNS-mixed
    case where a host returns both a public and a private A record.
    (Full DNS-rebinding defense — pinning the connection to the resolved
    IP — is a follow-up; see follow-up ticket
    clipper-ssrf-defense-followups.)
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ClipperBlockedHostError(
            f"Refusing scheme {parsed.scheme!r}; only http(s) is permitted"
        )
    host = parsed.hostname
    if not host:
        raise ClipperBlockedHostError(f"URL {url!r} has no host")

    # Try parsing the host directly as an IP literal first; that catches
    # http://127.0.0.1/ and http://[::1]/ without a DNS lookup.
    try:
        ip = ipaddress.ip_address(host)
        _reject_if_blocked(ip, host)
        return
    except ValueError:
        pass  # not an IP literal — resolve via DNS

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ClipperBlockedHostError(
            f"Could not resolve host {host!r}: {exc}"
        ) from exc

    seen: set[str] = set()
    for info in infos:
        addr = info[4][0]
        if addr in seen:
            continue
        seen.add(addr)
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue  # unparseable; skip rather than fail open
        _reject_if_blocked(ip, host)


def _reject_if_blocked(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address, host: str
) -> None:
    """Raise ClipperBlockedHostError if `ip` is on the SSRF blocklist."""
    # The stdlib classifiers cover loopback (127.0.0.0/8, ::1/128),
    # link-local (169.254.0.0/16 incl. AWS metadata, fe80::/10),
    # private (RFC1918 v4, fc00::/7), unspecified (0.0.0.0, ::),
    # reserved, and multicast.
    if (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_unspecified
        or ip.is_reserved
        or ip.is_multicast
    ):
        raise ClipperBlockedHostError(
            f"Refusing to fetch {host!r}: resolved IP {ip} is on the SSRF blocklist"
        )


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
        logger.warning("HTML title extraction failed", exc_info=True)
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

        Raises:
            ClipperBlockedHostError: if ``url`` uses a non-http(s) scheme
                or resolves to a loopback / link-local / RFC1918 private /
                reserved address. The check runs before any HTTP request.
        """
        _check_url_safe(url)

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
