"""Site cache service — renders /site pages to static HTML files for fast serving."""

import logging
from pathlib import Path

from ..config import PyriteConfig
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)

# Minimal HTML template — matches the site layout structure
_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="{og_type}">
{extra_head}
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 48rem; margin: 0 auto; padding: 2rem 1.5rem; color: #18181b; line-height: 1.6; }}
a {{ color: #b8860b; text-decoration: none; }} a:hover {{ text-decoration: underline; }}
h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }} h2 {{ font-size: 1.5rem; margin-top: 2rem; }} h3 {{ font-size: 1.25rem; margin-top: 1.5rem; }}
.badge {{ display: inline-block; padding: 0.1rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 500; }}
.tag {{ display: inline-block; background: #f4f4f5; padding: 0.1rem 0.6rem; border-radius: 1rem; font-size: 0.75rem; color: #71717a; margin: 0.1rem; }}
.entry-list a {{ display: block; padding: 0.75rem; border: 1px solid #e4e4e7; border-radius: 0.5rem; margin-bottom: 0.5rem; }}
.entry-list a:hover {{ border-color: #a1a1aa; text-decoration: none; }}
.breadcrumb {{ font-size: 0.875rem; color: #71717a; margin-bottom: 1rem; }}
.breadcrumb a {{ color: #71717a; }} .breadcrumb a:hover {{ color: #18181b; }}
.meta {{ font-size: 0.875rem; color: #71717a; margin-top: 0.5rem; }}
.links-section {{ margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #e4e4e7; }}
.links-section h2 {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #71717a; font-weight: 600; }}
footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e4e4e7; text-align: center; font-size: 0.75rem; color: #a1a1aa; }}
nav.site-header {{ display: flex; justify-content: space-between; align-items: center; padding-bottom: 1rem; margin-bottom: 2rem; border-bottom: 1px solid #e4e4e7; }}
nav.site-header a {{ color: #71717a; font-size: 0.875rem; margin-left: 1rem; }}
.kb-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(20rem, 1fr)); gap: 1rem; }}
.kb-card {{ border: 1px solid #e4e4e7; border-radius: 0.5rem; padding: 1.25rem; }} .kb-card:hover {{ border-color: #a1a1aa; }}
.kb-card h2 {{ font-size: 1.125rem; margin: 0 0 0.25rem 0; }}
.kb-card p {{ font-size: 0.875rem; color: #71717a; margin: 0 0 0.5rem 0; }}
</style>
</head>
<body>
<nav class="site-header">
<a href="/site" style="font-size:1.125rem;font-weight:bold;color:#18181b">Pyrite <span style="font-size:0.875rem;font-weight:normal;color:#71717a">Knowledge Base</span></a>
<div><a href="/site">Home</a><a href="/site/search">Search</a></div>
</nav>
{body}
<footer>Powered by <a href="https://pyrite.wiki">Pyrite</a> — Knowledge-as-Code</footer>
<script>
// Progressive enhancement: search widget
(function() {{
  var searchEl = document.getElementById('site-search');
  if (!searchEl) return;
  var input = searchEl.querySelector('input');
  var results = searchEl.querySelector('.search-results');
  if (!input || !results) return;
  var timer;
  input.addEventListener('input', function() {{
    clearTimeout(timer);
    var q = input.value.trim();
    if (!q) {{ results.innerHTML = ''; return; }}
    timer = setTimeout(function() {{
      fetch('/api/search?q=' + encodeURIComponent(q) + '&mode=hybrid&limit=20')
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
          results.innerHTML = (data.results || []).map(function(r) {{
            return '<a href="/site/' + r.kb_name + '/' + encodeURIComponent(r.id) + '">'
              + '<strong>' + r.title + '</strong> <small style="color:#71717a">' + r.entry_type + ' · ' + r.kb_name + '</small>'
              + (r.snippet ? '<br><small style="color:#71717a">' + r.snippet + '</small>' : '')
              + '</a>';
          }}).join('');
        }});
    }}, 300);
  }});
}})();
</script>
</body>
</html>"""

# schema.org type mapping
_SCHEMA_TYPES = {
    "note": "Article", "person": "Person", "organization": "Organization",
    "event": "Event", "source": "ScholarlyArticle", "concept": "Article",
    "writing": "Article", "era": "Article", "component": "SoftwareSourceCode",
}


class SiteCacheService:
    """Renders site pages to static HTML files."""

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db
        self.cache_dir = Path(config.settings.index_path).parent / "site-cache"

    def render_all(self) -> dict:
        """Render all KB index pages and entry pages. Returns stats."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        kbs = [
            {"name": kb.name, "description": getattr(kb, "description", ""), "entry_count": 0}
            for kb in self.config.knowledge_bases
        ]
        stats = {"kbs": 0, "entries": 0, "errors": 0}

        # Count entries per KB for landing page
        for kb_info in kbs:
            entries = self.db.list_entries(kb_name=kb_info["name"], limit=1)
            # Use a count query or list all
            all_entries = self.db.list_entries(kb_name=kb_info["name"], limit=10000)
            kb_info["entry_count"] = len(all_entries)

        # Render landing page
        self._render_landing(kbs)

        for kb_info in kbs:
            kb_name = kb_info["name"]
            kb_dir = self.cache_dir / kb_name
            kb_dir.mkdir(parents=True, exist_ok=True)

            # Render KB index
            entries = self.db.list_entries(kb_name=kb_name, limit=10000)
            self._render_kb_index(kb_info, entries)
            stats["kbs"] += 1

            # Render each entry
            for entry in entries:
                try:
                    full = self.db.get_entry(entry["id"], kb_name)
                    if full:
                        backlinks = self.db.get_backlinks(entry["id"], kb_name)
                        outlinks = self.db.get_outlinks(entry["id"], kb_name)
                        self._render_entry(kb_name, full, backlinks, outlinks)
                        stats["entries"] += 1
                except Exception as e:
                    logger.warning("Failed to render %s/%s: %s", kb_name, entry["id"], e)
                    stats["errors"] += 1

        return stats

    def render_entry_by_id(self, entry_id: str, kb_name: str) -> bool:
        """Render a single entry page. Returns True if successful."""
        entry = self.db.get_entry(entry_id, kb_name)
        if not entry:
            return False
        backlinks = self.db.get_backlinks(entry_id, kb_name)
        outlinks = self.db.get_outlinks(entry_id, kb_name)
        self._render_entry(kb_name, entry, backlinks, outlinks)
        return True

    def invalidate_entry(self, entry_id: str, kb_name: str):
        """Delete cached page for an entry."""
        path = self.cache_dir / kb_name / f"{entry_id}.html"
        path.unlink(missing_ok=True)
        # Also invalidate KB index since entry list changed
        (self.cache_dir / kb_name / "index.html").unlink(missing_ok=True)

    def invalidate_kb(self, kb_name: str):
        """Delete all cached pages for a KB."""
        import shutil
        kb_dir = self.cache_dir / kb_name
        if kb_dir.exists():
            shutil.rmtree(kb_dir)
        (self.cache_dir / "index.html").unlink(missing_ok=True)

    def _render_landing(self, kbs: list[dict]):
        """Render the /site landing page."""
        cards = []
        for kb in kbs:
            desc = f'<p>{_esc(kb.get("description", ""))}</p>' if kb.get("description") else ""
            entries = kb.get("entry_count", 0)
            cards.append(
                f'<a href="/site/{_esc(kb["name"])}" class="kb-card">'
                f'<h2>{_esc(kb["name"])}</h2>{desc}'
                f'<span style="font-size:0.75rem;color:#a1a1aa">{entries} entries</span></a>'
            )

        body = (
            '<h1>Knowledge Bases</h1>'
            '<p style="color:#71717a;margin-bottom:2rem">Browse curated knowledge bases on systems thinking, lean, agile, and more.</p>'
            '<div id="site-search" style="margin-bottom:2rem">'
            '<input type="text" placeholder="Search across all knowledge bases..." '
            'style="width:100%;padding:0.75rem 1rem;border:1px solid #e4e4e7;border-radius:0.5rem;font-size:1rem;outline:none">'
            '<div class="search-results entry-list" style="margin-top:0.5rem"></div>'
            '</div>'
            f'<div class="kb-grid">{"".join(cards)}</div>'
        )

        html = _PAGE_TEMPLATE.format(
            title="Pyrite Knowledge Base",
            description="Browse knowledge bases on systems thinking, lean, agile, and more.",
            og_title="Pyrite Knowledge Base",
            og_type="website",
            extra_head="",
            body=body,
        )
        (self.cache_dir / "index.html").write_text(html, encoding="utf-8")

    def _render_kb_index(self, kb: dict, entries: list[dict]):
        """Render a KB index page."""
        kb_name = kb["name"]
        desc = kb.get("description", "")
        total = len(entries)

        entry_html = []
        for e in entries:
            entry_html.append(
                f'<a href="/site/{_esc(kb_name)}/{_esc(e["id"])}">'
                f'<strong>{_esc(e.get("title", e["id"]))}</strong> '
                f'<span class="badge" style="background:#f4f4f5;color:#71717a">{_esc(e.get("entry_type", "note"))}</span>'
                f'</a>'
            )

        body = (
            f'<div class="breadcrumb"><a href="/site">Home</a> / <strong>{_esc(kb_name)}</strong></div>'
            f'<h1>{_esc(kb_name)}</h1>'
            f'<p style="color:#71717a">{total} entries</p>'
            + (f'<p style="color:#52525b;margin-bottom:2rem">{_esc(desc)}</p>' if desc else '')
            + f'<div class="entry-list">{"".join(entry_html)}</div>'
        )

        html = _PAGE_TEMPLATE.format(
            title=f"{kb_name} — Pyrite Knowledge Base",
            description=desc or f"Browse {total} entries in the {kb_name} knowledge base.",
            og_title=f"{kb_name} — Pyrite Knowledge Base",
            og_type="website",
            extra_head="",
            body=body,
        )
        (self.cache_dir / kb_name / "index.html").write_text(html, encoding="utf-8")

    def _render_entry(self, kb_name: str, entry: dict, backlinks: list, outlinks: list):
        """Render a single entry page."""
        entry_id = entry["id"]
        title = entry.get("title", entry_id)
        entry_type = entry.get("entry_type", "note")
        body_md = entry.get("body", "")
        summary = entry.get("summary", "")
        tags = entry.get("tags", []) or []
        date = entry.get("date", "")
        description = summary or (body_md[:160].replace("\n", " ") + "..." if len(body_md) > 160 else body_md.replace("\n", " "))

        # JSON-LD
        schema_type = _SCHEMA_TYPES.get(entry_type, "Article")
        jsonld = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "name": title,
            "description": description,
        }
        if date:
            jsonld["datePublished"] = date
        if tags:
            jsonld["keywords"] = ", ".join(tags)

        import json
        extra_head = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>'

        # Render body markdown to HTML (basic)
        body_html = _md_to_html(body_md, kb_name)

        # Tags
        tags_html = "".join(f'<span class="tag">{_esc(t)}</span>' for t in tags)
        tags_section = f'<div style="margin-top:0.75rem">{tags_html}</div>' if tags else ""

        # Backlinks
        bl_html = ""
        if backlinks:
            links = "".join(
                f'<a href="/site/{_esc(bl.get("kb_name", kb_name))}/{_esc(bl["id"])}">{_esc(bl.get("title", bl["id"]))}</a><br>'
                for bl in backlinks
            )
            bl_html = f'<div class="links-section"><h2>Linked from</h2>{links}</div>'

        # Outlinks
        ol_html = ""
        if outlinks:
            links = "".join(
                f'<a href="/site/{_esc(ol.get("kb_name", kb_name))}/{_esc(ol["id"])}">{_esc(ol.get("title", ol["id"]))}</a><br>'
                for ol in outlinks
            )
            ol_html = f'<div class="links-section"><h2>Links to</h2>{links}</div>'

        meta_parts = []
        if date:
            meta_parts.append(date)
        meta_parts.append(
            f'<a href="/entries/{_esc(entry_id)}?kb={_esc(kb_name)}" style="font-size:0.75rem;color:#a1a1aa">Edit on Pyrite</a>'
        )
        meta_html = f'<div class="meta">{" · ".join(meta_parts)}</div>'

        body = (
            f'<div class="breadcrumb"><a href="/site">Home</a> / '
            f'<a href="/site/{_esc(kb_name)}">{_esc(kb_name)}</a> / '
            f'<strong>{_esc(title)}</strong></div>'
            f'<h1>{_esc(title)} <span class="badge" style="background:#f4f4f5;color:#71717a">{_esc(entry_type)}</span></h1>'
            f'{tags_section}{meta_html}'
            f'<article style="margin-top:2rem">{body_html}</article>'
            f'{bl_html}{ol_html}'
        )

        html = _PAGE_TEMPLATE.format(
            title=f"{title} — {kb_name} | Pyrite",
            description=_esc(description),
            og_title=f"{title} — {kb_name}",
            og_type="article",
            extra_head=extra_head,
            body=body,
        )

        kb_dir = self.cache_dir / kb_name
        kb_dir.mkdir(parents=True, exist_ok=True)
        (kb_dir / f"{entry_id}.html").write_text(html, encoding="utf-8")


def _esc(text: str) -> str:
    """HTML-escape text."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _md_to_html(md: str, kb_name: str) -> str:
    """Convert basic markdown to HTML with wikilink resolution."""
    import re

    # Headings
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", md, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Bold/italic
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Wikilinks: [[kb:id|label]] or [[id|label]] or [[id]]
    def _wikilink(m: re.Match) -> str:
        target = m.group(1)
        label = m.group(2) if m.group(2) else None
        parts = target.split(":", 1)
        if len(parts) == 2:
            return f'<a href="/site/{_esc(parts[0])}/{_esc(parts[1])}">{_esc(label or parts[1])}</a>'
        return f'<a href="/site/{_esc(kb_name)}/{_esc(target)}">{_esc(label or target)}</a>'

    html = re.sub(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]", _wikilink, html)

    # Markdown links [text](url)
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # List items
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)

    # Paragraphs (double newline)
    html = re.sub(r"\n\n+", "</p><p>", html)
    html = f"<p>{html}</p>"

    # Clean up empty paragraphs around block elements
    html = re.sub(r"<p>\s*(<h[123]>)", r"\1", html)
    html = re.sub(r"(</h[123]>)\s*</p>", r"\1", html)
    html = re.sub(r"<p>\s*</p>", "", html)

    return html
