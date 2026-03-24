"""Site cache service — renders /site pages to static HTML files for fast serving."""

import logging
from pathlib import Path

from ..config import PyriteConfig
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)

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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root {{
  --gold: #996b1f;
  --gold-light: #c4951a;
  --gold-bg: #fdf8ef;
  --gold-border: #e8d5a8;
  --ink: #1a1a1a;
  --ink-soft: #4a4a4a;
  --ink-muted: #8a8a8a;
  --ink-faint: #b5b5b5;
  --surface: #fafaf8;
  --border: #e5e2db;
  --border-light: #f0ede6;
  --card-hover: #f5f3ee;
}}
*,*::before,*::after {{ box-sizing: border-box; }}
body {{
  font-family: 'Source Serif 4', Georgia, 'Times New Roman', serif;
  max-width: 52rem; margin: 0 auto; padding: 0 1.5rem;
  color: var(--ink); line-height: 1.72; font-size: 1.0625rem;
  background: var(--surface);
  -webkit-font-smoothing: antialiased;
}}
a {{ color: var(--gold); text-decoration: none; transition: color 0.15s; }}
a:hover {{ color: var(--gold-light); text-decoration: underline; text-underline-offset: 2px; }}
h1,h2,h3 {{ font-family: 'DM Sans', 'Helvetica Neue', sans-serif; color: var(--ink); line-height: 1.25; }}
h1 {{ font-size: 2.25rem; font-weight: 700; margin: 0 0 0.75rem 0; letter-spacing: -0.02em; }}
h2 {{ font-size: 1.375rem; font-weight: 600; margin: 2.5rem 0 0.75rem 0; }}
h3 {{ font-size: 1.125rem; font-weight: 600; margin: 2rem 0 0.5rem 0; }}
p {{ margin: 0 0 1.25rem 0; }}
strong {{ font-weight: 600; }}
code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.875em; background: var(--border-light); padding: 0.15em 0.35em; border-radius: 3px; }}
blockquote {{ margin: 1.5rem 0; padding: 0.75rem 1.25rem; border-left: 3px solid var(--gold-border); background: var(--gold-bg); font-style: italic; color: var(--ink-soft); }}
li {{ margin-bottom: 0.35rem; }}
ul {{ padding-left: 1.5rem; }}

/* Header */
nav.site-header {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 1.25rem 0; margin-bottom: 2.5rem;
  border-bottom: 1px solid var(--border);
}}
nav.site-header .logo {{
  font-family: 'DM Sans', sans-serif; font-size: 1.125rem; font-weight: 600;
  color: var(--ink); text-decoration: none; display: flex; align-items: center; gap: 0.5rem;
}}
nav.site-header .logo:hover {{ color: var(--ink); text-decoration: none; }}
nav.site-header .logo-mark {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.75rem; height: 1.75rem; border-radius: 0.375rem;
  background: linear-gradient(135deg, var(--gold-light), var(--gold));
  color: white; font-size: 0.75rem; font-weight: 700;
}}
nav.site-header .logo-sub {{ font-weight: 400; color: var(--ink-muted); margin-left: 0.25rem; }}
nav.site-header nav a {{
  font-family: 'DM Sans', sans-serif; font-size: 0.8125rem; font-weight: 500;
  color: var(--ink-muted); margin-left: 1.5rem; text-transform: uppercase; letter-spacing: 0.06em;
  transition: color 0.15s;
}}
nav.site-header nav a:hover {{ color: var(--ink); text-decoration: none; }}

/* Breadcrumbs */
.breadcrumb {{
  font-family: 'DM Sans', sans-serif; font-size: 0.8125rem; color: var(--ink-muted);
  margin-bottom: 1.5rem; letter-spacing: 0.01em;
}}
.breadcrumb a {{ color: var(--ink-muted); }} .breadcrumb a:hover {{ color: var(--gold); }}
.breadcrumb .sep {{ margin: 0 0.4rem; opacity: 0.4; }}

/* Entry type badge */
.badge {{
  display: inline-block; padding: 0.2rem 0.6rem; border-radius: 0.25rem;
  font-family: 'DM Sans', sans-serif; font-size: 0.6875rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
  background: var(--border-light); color: var(--ink-muted);
  vertical-align: middle; margin-left: 0.5rem; position: relative; top: -2px;
}}

/* Tags */
.tags {{ margin: 0.75rem 0 0 0; display: flex; flex-wrap: wrap; gap: 0.375rem; }}
.tag {{
  display: inline-block; font-family: 'DM Sans', sans-serif;
  background: var(--gold-bg); border: 1px solid var(--gold-border);
  padding: 0.15rem 0.65rem; border-radius: 1rem;
  font-size: 0.75rem; font-weight: 500; color: var(--gold);
}}

/* Meta line */
.meta {{
  font-family: 'DM Sans', sans-serif; font-size: 0.8125rem;
  color: var(--ink-muted); margin-top: 0.5rem;
  display: flex; align-items: center; gap: 0.75rem;
}}
.meta a {{ color: var(--ink-faint); font-size: 0.75rem; }}
.meta a:hover {{ color: var(--gold); }}

/* Article body */
article {{ margin-top: 2.5rem; }}
article p {{ color: var(--ink-soft); }}
article h2 {{ border-bottom: 1px solid var(--border-light); padding-bottom: 0.5rem; }}
article a {{ text-decoration: underline; text-decoration-color: var(--gold-border); text-underline-offset: 2px; }}
article a:hover {{ text-decoration-color: var(--gold); }}

/* Link sections (backlinks, outlinks) */
.links-section {{
  margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border);
}}
.links-section h2 {{
  font-family: 'DM Sans', sans-serif; font-size: 0.6875rem;
  text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-muted);
  font-weight: 600; margin: 0 0 0.75rem 0; border: none; padding: 0;
}}
.links-section a {{
  display: inline-block; font-size: 0.9375rem; margin-bottom: 0.375rem;
  text-decoration: none; margin-right: 0.25rem;
}}
.links-section a::before {{ content: '\2192\00a0'; color: var(--ink-faint); font-size: 0.8125rem; }}

/* Entry list (KB index, search results) */
.entry-list {{ margin-top: 1rem; }}
.entry-list a {{
  display: flex; align-items: baseline; gap: 0.625rem;
  padding: 0.75rem 1rem; border: 1px solid var(--border);
  border-radius: 0.5rem; margin-bottom: 0.5rem;
  background: white; transition: all 0.15s;
  text-decoration: none;
}}
.entry-list a:hover {{
  border-color: var(--gold-border); background: var(--gold-bg);
  text-decoration: none; box-shadow: 0 1px 3px rgba(153,107,31,0.06);
}}
.entry-list a strong {{ font-family: 'DM Sans', sans-serif; font-weight: 500; color: var(--ink); }}
.entry-list a .badge {{ margin-left: auto; flex-shrink: 0; }}

/* KB grid (landing page) */
.kb-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(22rem, 1fr)); gap: 1rem; }}
.kb-card {{
  border: 1px solid var(--border); border-radius: 0.625rem;
  padding: 1.5rem; background: white;
  transition: all 0.2s; text-decoration: none; display: block;
}}
.kb-card:hover {{
  border-color: var(--gold-border); box-shadow: 0 2px 8px rgba(153,107,31,0.08);
  text-decoration: none; transform: translateY(-1px);
}}
.kb-card h2 {{
  font-family: 'DM Sans', sans-serif; font-size: 1.0625rem;
  font-weight: 600; margin: 0 0 0.375rem 0; color: var(--ink);
}}
.kb-card p {{ font-size: 0.875rem; color: var(--ink-muted); margin: 0 0 0.75rem 0; line-height: 1.5; }}
.kb-card .count {{
  font-family: 'DM Sans', sans-serif; font-size: 0.75rem; font-weight: 500;
  color: var(--ink-faint); display: flex; align-items: center; gap: 0.375rem;
}}
.kb-card .count::before {{ content: ''; display: inline-block; width: 4px; height: 4px; border-radius: 50%; background: var(--gold); }}

/* Search */
#site-search {{ margin-bottom: 2.5rem; }}
#site-search input {{
  width: 100%; padding: 0.875rem 1.125rem;
  border: 1px solid var(--border); border-radius: 0.5rem;
  font-family: 'DM Sans', sans-serif; font-size: 0.9375rem;
  background: white; color: var(--ink); outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}}
#site-search input:focus {{
  border-color: var(--gold-border);
  box-shadow: 0 0 0 3px rgba(153,107,31,0.08);
}}
#site-search input::placeholder {{ color: var(--ink-faint); }}

/* Footer */
footer {{
  margin-top: 4rem; padding: 1.5rem 0;
  border-top: 1px solid var(--border);
  text-align: center; font-family: 'DM Sans', sans-serif;
  font-size: 0.75rem; color: var(--ink-faint); letter-spacing: 0.01em;
}}
footer a {{ color: var(--ink-muted); }}

/* Responsive */
@media (max-width: 640px) {{
  body {{ font-size: 1rem; padding: 0 1rem; }}
  h1 {{ font-size: 1.75rem; }}
  .kb-grid {{ grid-template-columns: 1fr; }}
  nav.site-header {{ flex-direction: column; gap: 0.75rem; align-items: flex-start; }}
  nav.site-header nav a {{ margin-left: 0; margin-right: 1rem; }}
}}
</style>
</head>
<body>
<nav class="site-header">
<a href="/site" class="logo"><span class="logo-mark">Py</span> Pyrite<span class="logo-sub">Knowledge Base</span></a>
<nav><a href="/site">Home</a><a href="/site/search">Search</a></nav>
</nav>
{body}
<footer>Powered by <a href="https://pyrite.wiki">Pyrite</a> &mdash; Knowledge&#8209;as&#8209;Code</footer>
<script>
(function() {{
  var s = document.getElementById('site-search');
  if (!s) return;
  var i = s.querySelector('input'), r = s.querySelector('.search-results');
  if (!i || !r) return;
  var t;
  i.addEventListener('input', function() {{
    clearTimeout(t);
    var q = i.value.trim();
    if (!q) {{ r.innerHTML = ''; return; }}
    t = setTimeout(function() {{
      fetch('/api/search?q=' + encodeURIComponent(q) + '&mode=hybrid&limit=20')
        .then(function(x) {{ return x.json(); }})
        .then(function(d) {{
          r.innerHTML = (d.results || []).map(function(e) {{
            return '<a href="/site/' + e.kb_name + '/' + encodeURIComponent(e.id) + '">'
              + '<strong>' + e.title + '</strong>'
              + '<span class="badge">' + e.entry_type + '</span>'
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
                f'<span class="count">{entries} entries</span></a>'
            )

        body = (
            '<h1>Knowledge Bases</h1>'
            '<p style="color:var(--ink-muted);margin-bottom:0.5rem">Curated knowledge bases on systems thinking, lean, agile, and more.</p>'
            '<div id="site-search">'
            '<input type="text" placeholder="Search across all knowledge bases...">'
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
            f'<div class="breadcrumb"><a href="/site">Home</a><span class="sep">/</span><strong>{_esc(kb_name)}</strong></div>'
            f'<h1>{_esc(kb_name)}</h1>'
            f'<p class="meta">{total} entries</p>'
            + (f'<p style="color:var(--ink-soft);margin-bottom:2rem">{_esc(desc)}</p>' if desc else '')
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
        tags_section = f'<div class="tags">{tags_html}</div>' if tags else ""

        # Backlinks
        bl_html = ""
        if backlinks:
            links = "".join(
                f'<a href="/site/{_esc(bl.get("kb_name", kb_name))}/{_esc(bl["id"])}">{_esc(bl.get("title", bl["id"]))}</a> '
                for bl in backlinks
            )
            bl_html = f'<div class="links-section"><h2>Linked from</h2>{links}</div>'

        # Outlinks
        ol_html = ""
        if outlinks:
            links = "".join(
                f'<a href="/site/{_esc(ol.get("kb_name", kb_name))}/{_esc(ol["id"])}">{_esc(ol.get("title", ol["id"]))}</a> '
                for ol in outlinks
            )
            ol_html = f'<div class="links-section"><h2>Links to</h2>{links}</div>'

        meta_parts = []
        if date:
            meta_parts.append(date)
        meta_parts.append(
            f'<a href="/entries/{_esc(entry_id)}?kb={_esc(kb_name)}">Edit on Pyrite</a>'
        )
        meta_html = f'<div class="meta">{" &middot; ".join(meta_parts)}</div>'

        body = (
            f'<div class="breadcrumb"><a href="/site">Home</a><span class="sep">/</span>'
            f'<a href="/site/{_esc(kb_name)}">{_esc(kb_name)}</a><span class="sep">/</span>'
            f'<strong>{_esc(title)}</strong></div>'
            f'<h1>{_esc(title)}<span class="badge">{_esc(entry_type)}</span></h1>'
            f'{tags_section}{meta_html}'
            f'<article>{body_html}</article>'
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
