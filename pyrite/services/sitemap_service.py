"""Sitemap generation for SEO indexing of the live app.

Enumerates entries in public KBs as a sitemap.xml document per the
`sitemaps.org` schema. Used by GET /sitemap.xml.

**Public signal (V1).**  Until `kb.yaml: published: true` ships as a
separate backlog item, we use `default_role == "read"` as the
"this KB is publicly readable" signal.  KBs without that setting are
assumed private and excluded from the sitemap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

from ..config import PyriteConfig
from ..storage.database import PyriteDB

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


@dataclass(frozen=True)
class SitemapEntry:
    """One URL entry in the rendered sitemap."""

    loc: str
    lastmod: str | None = None
    changefreq: str = "weekly"
    priority: str = "0.6"


class SitemapService:
    """Builds sitemap.xml content from the database."""

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db

    def _public_kb_names(self) -> list[str]:
        """Return the names of KBs considered public for sitemap purposes."""
        return [kb.name for kb in self.config.knowledge_bases if kb.default_role == "read"]

    def entries(self, site_url: str) -> list[SitemapEntry]:
        """Collect all public-KB entries as SitemapEntry objects.

        site_url is the canonical host prefix (e.g.
        "https://investigate.transparencycascade.org"); may be empty, in
        which case the caller's path-only URLs are emitted.
        """
        base = site_url.rstrip("/")
        out: list[SitemapEntry] = []

        for kb_name in self._public_kb_names():
            rows = self.db.list_entries(kb_name=kb_name, limit=100_000)
            for row in rows:
                if row.get("lifecycle") == "retired":
                    continue
                entry_id = row.get("id")
                if not entry_id:
                    continue
                out.append(
                    SitemapEntry(
                        loc=f"{base}/entries/{entry_id}?kb={kb_name}",
                        lastmod=_format_lastmod(row),
                        changefreq="weekly",
                        priority="0.6",
                    )
                )
        return out

    def render_xml(self, site_url: str) -> str:
        """Build the full sitemap XML document."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<urlset xmlns="{SITEMAP_NS}">',
        ]
        for e in self.entries(site_url):
            lines.append("  <url>")
            lines.append(f"    <loc>{escape(e.loc)}</loc>")
            if e.lastmod:
                lines.append(f"    <lastmod>{escape(e.lastmod)}</lastmod>")
            lines.append(f"    <changefreq>{e.changefreq}</changefreq>")
            lines.append(f"    <priority>{e.priority}</priority>")
            lines.append("  </url>")
        lines.append("</urlset>")
        return "\n".join(lines) + "\n"

    def render_robots(self, site_url: str) -> str:
        """Build a robots.txt pointing at the sitemap."""
        sitemap_url = f"{site_url.rstrip('/')}/sitemap.xml" if site_url else "/sitemap.xml"
        return f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n"


def _format_lastmod(row: dict[str, Any]) -> str | None:
    """Pick the best timestamp from a row and stringify it.

    Skips values that aren't parseable as a date (e.g. the literal
    string 'CURRENT_TIMESTAMP' that sqlite leaves in indexed_at when
    a row is inserted directly). Sitemaps prefer ISO-8601; we accept
    SQLite "YYYY-MM-DD HH:MM:SS" and convert.
    """
    for key in ("updated_at", "created_at", "indexed_at"):
        val = row.get(key)
        if not val:
            continue
        s = str(val)
        # Reject non-date shapes (first 4 chars must be a year).
        if not (len(s) >= 4 and s[:4].isdigit()):
            continue
        return s.replace(" ", "T") if " " in s and "T" not in s else s
    return None
