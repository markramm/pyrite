"""Site cache service — renders /site pages to static HTML files for fast serving."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..config import PyriteConfig
from ..storage.database import PyriteDB
from ..utils.metadata import parse_metadata
from ..utils.sanitize import sanitize_filename

logger = logging.getLogger(__name__)

# Jinja2 template environment — loads from pyrite/server/templates/
_TEMPLATE_DIR = Path(__file__).parent.parent / "server" / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,  # We handle escaping explicitly via _esc()
)


def _render_template(template_name: str, **kwargs: object) -> str:
    """Render a Jinja2 template with the given context."""
    tmpl = _jinja_env.get_template(template_name)
    return tmpl.render(**kwargs)


_PAGE_TEMPLATE_LEGACY = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="robots" content="index, follow">
{canonical}
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="{og_type}">
{og_url_meta}
{og_image_meta}
{twitter_meta}
{extra_head}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root {{
  --gold: #C9A84C;
  --gold-dim: #B8942F;
  --gold-glow: rgba(201,168,76,0.12);
  --gold-border: rgba(201,168,76,0.25);
  --surface: #18181b;
  --surface-raised: #1f1f23;
  --surface-overlay: #27272a;
  --ink: #e4e4e7;
  --ink-soft: #a1a1aa;
  --ink-muted: #71717a;
  --ink-faint: #52525b;
  --border: #2e2e33;
  --border-light: #3f3f46;
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
a:hover {{ color: var(--gold-dim); text-decoration: underline; text-underline-offset: 2px; }}
h1,h2,h3 {{ font-family: 'DM Sans', 'Helvetica Neue', sans-serif; color: var(--ink); line-height: 1.25; }}
h1 {{ font-size: 2.25rem; font-weight: 700; margin: 0 0 0.75rem 0; letter-spacing: -0.02em; }}
h2 {{ font-size: 1.375rem; font-weight: 600; margin: 2.5rem 0 0.75rem 0; }}
h3 {{ font-size: 1.125rem; font-weight: 600; margin: 2rem 0 0.5rem 0; }}
p {{ margin: 0 0 1.25rem 0; }}
strong {{ font-weight: 600; }}
code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.875em; background: var(--surface-overlay); padding: 0.15em 0.35em; border-radius: 3px; color: var(--ink); }}
blockquote {{ margin: 1.5rem 0; padding: 0.75rem 1.25rem; border-left: 3px solid var(--gold-border); background: var(--surface-raised); font-style: italic; color: var(--ink-soft); }}
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
  background: linear-gradient(135deg, var(--gold), var(--gold-dim));
  color: var(--surface); font-size: 0.75rem; font-weight: 700;
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
  background: var(--surface-overlay); color: var(--ink-muted);
  vertical-align: middle; margin-left: 0.5rem; position: relative; top: -2px;
}}

/* Tags */
.tags {{ margin: 0.75rem 0 0 0; display: flex; flex-wrap: wrap; gap: 0.375rem; }}
.tag {{
  display: inline-block; font-family: 'DM Sans', sans-serif;
  background: var(--gold-glow); border: 1px solid var(--gold-border);
  padding: 0.15rem 0.65rem; border-radius: 1rem;
  font-size: 0.75rem; font-weight: 500; color: var(--gold);
}}

/* Status badge color variants */
.badge-status {{
  display: inline-block; padding: 0.2rem 0.6rem; border-radius: 0.25rem;
  font-family: 'DM Sans', sans-serif; font-size: 0.6875rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
  vertical-align: middle; margin-left: 0.5rem; position: relative; top: -2px;
}}
.badge-status.status-confirmed {{ background: rgba(34,197,94,0.15); color: #4ade80; }}
.badge-status.status-reported,
.badge-status.status-alleged,
.badge-status.status-rumored {{ background: rgba(245,158,11,0.15); color: #fbbf24; }}
.badge-status.status-disputed {{ background: rgba(239,68,68,0.15); color: #f87171; }}
.badge-status.status-draft {{ background: var(--surface-overlay); color: var(--ink-muted); }}

/* Actors section */
.actors {{
  font-family: 'DM Sans', sans-serif; font-size: 0.875rem;
  margin-top: 0.75rem; color: var(--ink-soft);
}}
.actors .label {{
  font-weight: 600; color: var(--ink-muted); font-size: 0.75rem;
  text-transform: uppercase; letter-spacing: 0.06em; margin-right: 0.5rem;
}}
.actors a {{ color: var(--gold); font-size: 0.875rem; }}
.actors a:hover {{ color: var(--gold-dim); }}

/* Capture lane badges */
.capture-lanes {{ margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 0.375rem; }}
.lane-badge {{
  display: inline-block; font-family: 'DM Sans', sans-serif;
  background: var(--surface-overlay); border: 1px solid var(--border);
  padding: 0.1rem 0.55rem; border-radius: 0.25rem;
  font-size: 0.6875rem; font-weight: 500; color: var(--ink-muted);
  text-transform: lowercase;
}}

/* Sources section */
.sources-section {{
  margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border);
}}
.sources-section h2 {{
  font-family: 'DM Sans', sans-serif; font-size: 0.6875rem;
  text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-muted);
  font-weight: 600; margin: 0 0 0.75rem 0; border: none; padding: 0;
}}
.sources-section ol {{
  padding-left: 1.5rem; margin: 0;
}}
.sources-section li {{
  font-size: 0.875rem; color: var(--ink-soft); margin-bottom: 0.5rem; line-height: 1.5;
}}
.sources-section a {{ color: var(--gold); }}
.sources-section a:hover {{ color: var(--gold-dim); }}
.sources-section .outlet {{ color: var(--ink-muted); }}
.sources-section .source-date {{ color: var(--ink-faint); }}

/* Meta line */
.meta {{
  font-family: 'DM Sans', sans-serif; font-size: 0.8125rem;
  color: var(--ink-muted); margin-top: 0.5rem;
  display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
}}
.meta a {{ color: var(--ink-faint); font-size: 0.75rem; }}
.meta a:hover {{ color: var(--gold); }}

/* Article body */
article {{ margin-top: 2.5rem; }}
article p {{ color: var(--ink-soft); }}
article h2 {{ border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
article a {{ text-decoration: underline; text-decoration-color: var(--gold-border); text-underline-offset: 2px; }}
article a:hover {{ text-decoration-color: var(--gold); }}
article ul {{ color: var(--ink-soft); }}
article li {{ color: var(--ink-soft); }}

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

/* Coverage section (cross-KB backlinks with external URLs) */
.coverage-section {{
  margin-top: 2.5rem; padding: 1.25rem; border-radius: 0.5rem;
  background: var(--gold-glow); border: 1px solid var(--gold-border);
}}
.coverage-section h2 {{
  font-family: 'DM Sans', sans-serif; font-size: 0.75rem;
  text-transform: uppercase; letter-spacing: 0.08em; color: var(--gold);
  margin: 0 0 0.75rem 0;
}}
.coverage-list {{
  display: flex; flex-direction: column; gap: 0.375rem;
}}
.coverage-list a {{
  font-size: 0.9375rem; font-weight: 500; color: var(--gold);
}}
.coverage-list a:hover {{ color: var(--gold-dim); }}
.coverage-pub {{ font-size: 0.8125rem; color: var(--ink-muted); font-weight: 400; }}

/* Related events section */
.related-section {{
  margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border);
}}
.related-section h2 {{
  font-family: 'DM Sans', sans-serif; font-size: 0.6875rem;
  text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-muted);
  font-weight: 600; margin: 0 0 0.75rem 0; border: none; padding: 0;
}}
.related-list {{
  display: flex; flex-direction: column; gap: 0.375rem;
}}
.related-list a {{
  display: inline-block; font-size: 0.9375rem;
  text-decoration: none; margin-right: 0.25rem;
}}
.related-list a::before {{ content: '\2192\00a0'; color: var(--ink-faint); font-size: 0.8125rem; }}
.related-list .date {{ font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: var(--ink-faint); margin-left: 0.5rem; }}

/* Entry list (KB index, search results) */
.entry-list {{ margin-top: 1rem; }}
.entry-list a {{
  display: flex; align-items: baseline; gap: 0.625rem;
  padding: 0.75rem 1rem; border: 1px solid var(--border);
  border-radius: 0.5rem; margin-bottom: 0.5rem;
  background: var(--surface-raised); transition: all 0.15s;
  text-decoration: none;
}}
.entry-list a:hover {{
  border-color: var(--gold-border); background: var(--gold-glow);
  text-decoration: none; box-shadow: 0 1px 6px rgba(201,168,76,0.08);
}}
.entry-list a strong {{ font-family: 'DM Sans', sans-serif; font-weight: 500; color: var(--ink); }}
.entry-list a .badge {{ margin-left: auto; flex-shrink: 0; }}

/* KB grid (landing page) */
.kb-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(22rem, 1fr)); gap: 1rem; }}
.kb-card {{
  border: 1px solid var(--border); border-radius: 0.625rem;
  padding: 1.5rem; background: var(--surface-raised);
  transition: all 0.2s; text-decoration: none; display: block;
}}
.kb-card:hover {{
  border-color: var(--gold-border); box-shadow: 0 2px 12px rgba(201,168,76,0.1);
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
  background: var(--surface-raised); color: var(--ink); outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}}
#site-search input:focus {{
  border-color: var(--gold-border);
  box-shadow: 0 0 0 3px rgba(201,168,76,0.1);
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
/* Reading time + heading anchors */
.reading-time {{
  font-family: 'DM Sans', sans-serif; font-size: 0.8125rem;
  color: var(--ink-faint); font-style: italic;
}}
h2[id], h3[id] {{ position: relative; }}
h2[id]:hover .anchor, h3[id]:hover .anchor {{ opacity: 1; }}
.anchor {{
  position: absolute; left: -1.25rem; top: 50%; transform: translateY(-50%);
  color: var(--ink-faint); text-decoration: none; opacity: 0;
  transition: opacity 0.15s; font-size: 0.875rem;
}}
.anchor:hover {{ color: var(--gold); text-decoration: none; }}

/* Table of contents */
.toc {{
  font-family: 'DM Sans', sans-serif; font-size: 0.8125rem;
  border: 1px solid var(--border); border-radius: 0.5rem;
  padding: 1rem 1.25rem; margin-bottom: 2rem; background: var(--surface-raised);
}}
.toc-title {{
  font-weight: 600; font-size: 0.6875rem; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--ink-muted); margin-bottom: 0.5rem;
}}
.toc ol {{ padding-left: 1.25rem; margin: 0; }}
.toc li {{ margin-bottom: 0.25rem; line-height: 1.4; }}
.toc a {{ color: var(--ink-soft); }} .toc a:hover {{ color: var(--gold); }}

/* Back to top */
.back-to-top {{
  display: none; position: fixed; bottom: 2rem; right: 2rem;
  width: 2.5rem; height: 2.5rem; border-radius: 50%;
  background: var(--surface-raised); border: 1px solid var(--border);
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  cursor: pointer; align-items: center; justify-content: center;
  transition: all 0.2s; z-index: 100; font-size: 1rem; color: var(--ink-muted);
}}
.back-to-top:hover {{ border-color: var(--gold-border); color: var(--gold); transform: translateY(-2px); }}
.back-to-top.visible {{ display: flex; }}

@media (max-width: 640px) {{
  body {{ font-size: 1rem; padding: 0 1rem; }}
  h1 {{ font-size: 1.75rem; }}
  .kb-grid {{ grid-template-columns: 1fr; }}
  nav.site-header {{ flex-direction: column; gap: 0.75rem; align-items: flex-start; }}
  nav.site-header nav a {{ margin-left: 0; margin-right: 1rem; }}
  .toc {{ display: none; }}
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
<button class="back-to-top" id="btt" aria-label="Back to top">&uarr;</button>
<script>
(function() {{
  function esc(s) {{ var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}

  /* Search widget */
  var s = document.getElementById('site-search');
  if (s) {{
    var i = s.querySelector('input'), r = s.querySelector('.search-results'), t;
    if (i && r) i.addEventListener('input', function() {{
      clearTimeout(t); var q = i.value.trim();
      if (!q) {{ r.innerHTML = ''; return; }}
      t = setTimeout(function() {{
        fetch('/api/search?q=' + encodeURIComponent(q) + '&mode=hybrid&limit=20')
          .then(function(x) {{ return x.json(); }})
          .then(function(d) {{
            r.innerHTML = (d.results || []).map(function(e) {{
              return '<a href="/site/' + esc(e.kb_name) + '/' + encodeURIComponent(e.id) + '">'
                + '<strong>' + esc(e.title) + '</strong><span class="badge">' + esc(e.entry_type) + '</span></a>';
            }}).join('');
          }});
      }}, 300);
    }});
  }}

  /* Heading anchors + TOC generation */
  var article = document.querySelector('article');
  if (article) {{
    var headings = article.querySelectorAll('h2, h3');
    var tocItems = [];
    headings.forEach(function(h, idx) {{
      var id = h.textContent.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'section-' + idx;
      h.id = id;
      var a = document.createElement('a'); a.className = 'anchor'; a.href = '#' + id; a.textContent = '#';
      a.setAttribute('aria-label', 'Link to this section');
      h.insertBefore(a, h.firstChild);
      tocItems.push({{ id: id, text: h.textContent.replace(/^#\\s*/, ''), level: h.tagName }});
    }});
    /* Insert TOC if 3+ headings */
    if (tocItems.length >= 3) {{
      var toc = document.createElement('div'); toc.className = 'toc';
      var title = document.createElement('div'); title.className = 'toc-title'; title.textContent = 'Contents';
      var ol = document.createElement('ol');
      tocItems.forEach(function(item) {{
        var li = document.createElement('li');
        if (item.level === 'H3') li.style.marginLeft = '1rem';
        li.innerHTML = '<a href="#' + item.id + '">' + item.text + '</a>';
        ol.appendChild(li);
      }});
      toc.appendChild(title); toc.appendChild(ol);
      article.insertBefore(toc, article.firstChild);
    }}
  }}

  /* Back to top */
  var btt = document.getElementById('btt');
  if (btt) {{
    window.addEventListener('scroll', function() {{
      btt.classList.toggle('visible', window.scrollY > 400);
    }});
    btt.addEventListener('click', function() {{ window.scrollTo({{ top: 0, behavior: 'smooth' }}); }});
  }}

  /* Smooth scroll for anchor links */
  document.querySelectorAll('a[href^="#"]').forEach(function(a) {{
    a.addEventListener('click', function(e) {{
      var target = document.querySelector(a.getAttribute('href'));
      if (target) {{ e.preventDefault(); target.scrollIntoView({{ behavior: 'smooth', block: 'start' }}); }}
    }});
  }});
}})();
</script>
</body>
</html>"""


def _render_page(**kwargs: object) -> str:
    """Render a page using Jinja2 template, falling back to legacy format string."""
    try:
        return _render_template("base.html", **kwargs)
    except Exception:
        # Build legacy meta tag strings from structured params
        og_url = kwargs.pop("og_url", "") if "og_url" in kwargs else ""
        og_image = kwargs.pop("og_image", "") if "og_image" in kwargs else ""
        twitter_card = kwargs.pop("twitter_card", "") if "twitter_card" in kwargs else ""
        kwargs["og_url_meta"] = f'<meta property="og:url" content="{og_url}">' if og_url else ""
        kwargs["og_image_meta"] = f'<meta property="og:image" content="{og_image}">' if og_image else ""
        if twitter_card:
            kwargs["twitter_meta"] = (
                f'<meta name="twitter:card" content="{twitter_card}">\n'
                f'<meta name="twitter:title" content="{kwargs.get("og_title", "")}">\n'
                f'<meta name="twitter:description" content="{kwargs.get("description", "")}">'
            )
        else:
            kwargs["twitter_meta"] = ""
        # Fall back to legacy template if Jinja2 fails
        return _PAGE_TEMPLATE_LEGACY.format(**kwargs)


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
        from collections import defaultdict

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        kbs = [
            {"name": kb.name, "description": getattr(kb, "description", ""), "entry_count": 0}
            for kb in self.config.knowledge_bases
        ]
        stats = {"kbs": 0, "entries": 0, "errors": 0}

        # Load all entries per KB (one query each, not per-entry)
        kb_entries: dict[str, list] = {}
        for kb_info in kbs:
            entries = self.db.list_entries(kb_name=kb_info["name"], limit=10000)
            kb_entries[kb_info["name"]] = entries
            kb_info["entry_count"] = len(entries)

        # Render landing page
        self._render_landing(kbs)

        for kb_info in kbs:
            kb_name = kb_info["name"]
            kb_dir = self.cache_dir / kb_name
            kb_dir.mkdir(parents=True, exist_ok=True)

            entries = kb_entries[kb_name]

            # Render KB index
            self._render_kb_index(kb_info, entries)
            stats["kbs"] += 1

            # Batch-load all backlinks and outlinks for this KB (2 queries total, not 2N)
            backlinks_map: dict[str, list] = defaultdict(list)
            outlinks_map: dict[str, list] = defaultdict(list)
            for entry in entries:
                eid = entry["id"]
                for bl in self.db.get_backlinks(eid, kb_name):
                    backlinks_map[eid].append(bl)
                for ol in self.db.get_outlinks(eid, kb_name):
                    outlinks_map[eid].append(ol)

            # Pre-compute actor->entry_ids and tag->entry_ids for related events
            actor_to_entries: dict[str, set[str]] = defaultdict(set)
            tag_to_entries: dict[str, set[str]] = defaultdict(set)
            entry_by_id: dict[str, dict] = {}
            for entry in entries:
                eid = entry["id"]
                entry_by_id[eid] = entry
                # Parse metadata
                meta = parse_metadata(entry.get("metadata"))
                actors = meta.get("actors") or meta.get("participants") or []
                if isinstance(actors, list):
                    for actor in actors:
                        if actor:
                            actor_to_entries[str(actor)].add(eid)
                for tag in entry.get("tags") or []:
                    if tag:
                        tag_to_entries[str(tag)].add(eid)

            # Compute related entries map: entry_id -> [(entry_dict, score), ...]
            related_map: dict[str, list[tuple[dict, int]]] = {}
            for entry in entries:
                eid = entry["id"]
                meta = parse_metadata(entry.get("metadata"))
                actors = meta.get("actors") or meta.get("participants") or []
                if not isinstance(actors, list):
                    actors = []
                tags = entry.get("tags") or []

                # IDs to exclude: self, backlinks, outlinks
                exclude = {eid}
                for bl in backlinks_map.get(eid, []):
                    exclude.add(bl["id"])
                for ol in outlinks_map.get(eid, []):
                    exclude.add(ol["id"])

                # Score candidates
                scores: dict[str, int] = defaultdict(int)
                for actor in actors:
                    if actor:
                        for candidate_id in actor_to_entries.get(str(actor), set()):
                            if candidate_id not in exclude:
                                scores[candidate_id] += 2
                for tag in tags:
                    if tag:
                        for candidate_id in tag_to_entries.get(str(tag), set()):
                            if candidate_id not in exclude:
                                scores[candidate_id] += 1

                if scores:
                    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
                    related_map[eid] = [
                        (entry_by_id[cid], score)
                        for cid, score in top
                        if cid in entry_by_id
                    ]

            # Check if KB is read-only (hide edit links on public sites)
            kb_config = self.config.get_kb(kb_name)
            is_read_only = kb_config.read_only if kb_config else False

            # Render each entry using pre-loaded data
            for entry in entries:
                try:
                    eid = entry["id"]
                    self._render_entry(
                        kb_name, entry,
                        backlinks_map.get(eid, []),
                        outlinks_map.get(eid, []),
                        read_only=is_read_only,
                        related=related_map.get(eid, []),
                    )
                    stats["entries"] += 1
                except Exception as e:
                    logger.warning("Failed to render %s/%s: %s", kb_name, eid, e)
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
            '<p style="color:var(--ink-soft);margin-bottom:0.5rem">Curated knowledge bases on systems thinking, lean, agile, and more.</p>'
            '<div id="site-search">'
            '<input type="text" placeholder="Search across all knowledge bases...">'
            '<div class="search-results entry-list" style="margin-top:0.5rem"></div>'
            '</div>'
            f'<div class="kb-grid">{"".join(cards)}</div>'
        )

        html = _render_page(
            title="Pyrite Knowledge Base",
            description="Browse knowledge bases on systems thinking, lean, agile, and more.",
            og_title="Pyrite Knowledge Base",
            og_type="website",
            og_url="/site",
            og_image="/static/favicon.svg",
            twitter_card="summary",
            extra_head="",
            canonical='<link rel="canonical" href="/site">',
            body=body,
        )
        (self.cache_dir / "index.html").write_text(html, encoding="utf-8")

    def _render_kb_index(self, kb: dict, entries: list[dict]):
        """Render a KB index page. Uses _homepage entry content if available."""
        kb_name = kb["name"]
        desc = kb.get("description", "")
        total = len(entries)

        # Check for a custom homepage entry
        homepage = self.db.get_entry("_homepage", kb_name)
        if homepage and homepage.get("body"):
            title = homepage.get("title", kb_name)
            has_about = self.db.get_entry("_about", kb_name) is not None
            body = _render_designed_homepage(homepage, kb_name, total, has_about=has_about)
            page_desc = homepage.get("summary") or desc or f"{total} entries in the {kb_name} knowledge base."
        else:
            # Auto-generated KB index
            title = kb_name
            entry_html = []
            for e in entries:
                entry_html.append(
                    f'<a href="/site/{_esc(kb_name)}/{_esc(e["id"])}">'
                    f'<strong>{_esc(e.get("title", e["id"]))}</strong> '
                    f'<span class="badge">{_esc(e.get("entry_type", "note"))}</span>'
                    f'</a>'
                )

            body = (
                f'<div class="breadcrumb"><a href="/site">Home</a><span class="sep">/</span><strong>{_esc(kb_name)}</strong></div>'
                f'<h1>{_esc(kb_name)}</h1>'
                f'<p class="meta">{total} entries</p>'
                + (f'<p style="color:var(--ink-soft);margin:1rem 0 2rem 0">{_esc(desc)}</p>' if desc else '')
                + '<div id="site-search" style="margin-bottom:1.5rem">'
                + f'<input type="text" placeholder="Search {_esc(kb_name)}...">'
                + '<div class="search-results entry-list" style="margin-top:0.5rem"></div></div>'
                + f'<div class="entry-list">{"".join(entry_html)}</div>'
            )
            page_desc = desc or f"Browse {total} entries in the {kb_name} knowledge base."

        html = _render_page(
            title=f"{_esc(title)} — Pyrite Knowledge Base",
            description=_esc(page_desc),
            og_title=f"{_esc(title)} — Pyrite Knowledge Base",
            og_type="website",
            og_url=f"/site/{_esc(kb_name)}",
            og_image="/static/favicon.svg",
            twitter_card="summary",
            extra_head="",
            canonical=f'<link rel="canonical" href="/site/{_esc(kb_name)}">',
            body=body,
        )
        (self.cache_dir / kb_name / "index.html").write_text(html, encoding="utf-8")

    def _render_entry(self, kb_name: str, entry: dict, backlinks: list, outlinks: list, *, read_only: bool = False, related: list[tuple[dict, int]] | None = None):
        """Render a single entry page."""
        import json

        entry_id = entry["id"]
        title = entry.get("title", entry_id)
        entry_type = entry.get("entry_type", "note")
        body_md = entry.get("body") or ""
        summary = entry.get("summary") or ""
        tags = entry.get("tags") or []
        date = entry.get("date") or ""
        status = entry.get("status") or ""
        location = entry.get("location") or ""
        description = summary or (body_md[:160].replace("\n", " ") + "..." if len(body_md) > 160 else body_md.replace("\n", " "))

        # Parse metadata (may be a JSON string or already a dict)
        metadata = parse_metadata(entry.get("metadata"))

        # Fetch sources — list_entries doesn't include them, so fetch via get_entry
        sources = entry.get("sources")
        if sources is None:
            full_entry = self.db.get_entry(entry_id, kb_name)
            sources = full_entry.get("sources", []) if full_entry else []

        # Canonical URL
        canonical_path = f"/site/{_esc(kb_name)}/{_esc(entry_id)}"
        canonical = f'<link rel="canonical" href="{canonical_path}">'

        # JSON-LD (enhanced with url, publisher, author)
        schema_type = _SCHEMA_TYPES.get(entry_type, "Article")
        jsonld = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "name": title,
            "description": description,
            "url": canonical_path,
            "publisher": {"@type": "Organization", "name": "Pyrite"},
        }
        if date:
            jsonld["datePublished"] = date
        if tags:
            jsonld["keywords"] = ", ".join(tags)
        # Author from created_by or provenance in metadata
        author_name = entry.get("created_by") or ""
        if not author_name:
            prov = metadata.get("provenance") or {}
            if isinstance(prov, dict):
                author_name = prov.get("created_by") or ""
        if author_name:
            jsonld["author"] = {"@type": "Person", "name": author_name}

        extra_head = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>'

        # Reading time estimate
        word_count = len(body_md.split())
        reading_mins = max(1, round(word_count / 230))

        # Render body markdown to HTML (basic)
        body_html = _md_to_html(body_md, kb_name)

        # Tags
        tags_html = "".join(f'<span class="tag">{_esc(t)}</span>' for t in tags)
        tags_section = f'<div class="tags">{tags_html}</div>' if tags else ""

        # Status badge (displayed next to type badge in h1)
        status_html = ""
        if status:
            status_lower = status.lower()
            if status_lower == "confirmed":
                css_class = "status-confirmed"
            elif status_lower in ("reported", "alleged", "rumored"):
                css_class = f"status-{status_lower}"
            elif status_lower == "disputed":
                css_class = "status-disputed"
            elif status_lower == "draft":
                css_class = "status-draft"
            else:
                css_class = "status-draft"
            status_html = f'<span class="badge-status {css_class}">{_esc(status)}</span>'

        # Actors / Participants
        actors = metadata.get("actors") or metadata.get("participants") or []
        actors_html = ""
        if actors and isinstance(actors, list):
            actor_links = ", ".join(
                f'<a href="/site/{_esc(kb_name)}?search={_esc(str(a))}">{_esc(str(a))}</a>'
                for a in actors
                if a
            )
            if actor_links:
                actors_html = f'<div class="actors"><span class="label">Actors:</span>{actor_links}</div>'

        # Capture lanes
        capture_lanes = metadata.get("capture_lanes") or []
        lanes_html = ""
        if capture_lanes and isinstance(capture_lanes, list):
            lane_badges = "".join(
                f'<span class="lane-badge">{_esc(str(lane))}</span>'
                for lane in capture_lanes
                if lane
            )
            if lane_badges:
                lanes_html = f'<div class="capture-lanes">{lane_badges}</div>'

        # Sources section (rendered before backlinks)
        sources_html = ""
        if sources:
            source_items = []
            for src in sources:
                if not isinstance(src, dict):
                    continue
                src_title = _esc(str(src.get("title") or "Untitled"))
                src_url = src.get("url") or ""
                src_outlet = _esc(str(src.get("outlet") or ""))
                src_date = _esc(str(src.get("date") or ""))

                # Only render href for http/https URLs
                if src_url and isinstance(src_url, str) and src_url.lower().startswith(("http://", "https://")):
                    title_part = f'<a href="{_esc(src_url)}" target="_blank" rel="noopener">{src_title}</a>'
                else:
                    title_part = src_title

                parts = [title_part]
                if src_outlet:
                    parts.append(f'<span class="outlet">{src_outlet}</span>')
                if src_date:
                    parts.append(f'<span class="source-date">({src_date})</span>')
                source_items.append(f'<li>{" &mdash; ".join(parts)}</li>')

            if source_items:
                sources_html = (
                    f'<div class="sources-section"><h2>Sources</h2>'
                    f'<ol>{"".join(source_items)}</ol></div>'
                )

        # Related events (entries sharing actors/tags, excluding self/backlinks/outlinks)
        related_html = ""
        if related:
            related_items = []
            for rel_entry, _score in related:
                rel_id = rel_entry["id"]
                rel_title = rel_entry.get("title", rel_id)
                rel_date = rel_entry.get("date") or ""
                date_span = f' <span class="date">{_esc(rel_date)}</span>' if rel_date else ""
                related_items.append(
                    f'<a href="/site/{_esc(kb_name)}/{_esc(rel_id)}">{_esc(rel_title)}</a>{date_span}'
                )
            if related_items:
                related_html = (
                    f'<div class="related-section"><h2>Related Events</h2>'
                    f'<div class="related-list">{"".join(related_items)}</div></div>'
                )

        # Coverage — from the entry's own coverage frontmatter field
        # Format: coverage: [{title, url, publication}, ...]
        coverage_html = ""
        coverage_data = metadata.get("coverage") or []
        if isinstance(coverage_data, list) and coverage_data:
            coverage_items = []
            for cov in coverage_data:
                if not isinstance(cov, dict):
                    continue
                cov_title = _esc(cov.get("title", ""))
                cov_url = cov.get("url", "")
                cov_pub = _esc(cov.get("publication", ""))
                if cov_url and isinstance(cov_url, str) and cov_url.startswith(("http://", "https://")):
                    pub_span = f' <span class="coverage-pub">— {cov_pub}</span>' if cov_pub else ""
                    coverage_items.append(
                        f'<a href="{_esc(cov_url)}" target="_blank" rel="noopener noreferrer">{cov_title or _esc(cov_url)}</a>{pub_span}'
                    )
            if coverage_items:
                coverage_html = (
                    f'<div class="coverage-section"><h2>Coverage</h2>'
                    f'<div class="coverage-list">{"".join(coverage_items)}</div></div>'
                )

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
            meta_parts.append(_esc(date))
        if location:
            meta_parts.append(f'<span>{_esc(location)}</span>')
        meta_parts.append(f'<span class="reading-time">{reading_mins} min read</span>')
        if not read_only:
            meta_parts.append(
                f'<a href="/entries/{_esc(entry_id)}?kb={_esc(kb_name)}">Edit on Pyrite</a>'
            )
        meta_html = f'<div class="meta">{" &middot; ".join(meta_parts)}</div>'

        body = (
            f'<div class="breadcrumb"><a href="/site">Home</a><span class="sep">/</span>'
            f'<a href="/site/{_esc(kb_name)}">{_esc(kb_name)}</a><span class="sep">/</span>'
            f'<strong>{_esc(title)}</strong></div>'
            f'<h1>{_esc(title)}<span class="badge">{_esc(entry_type)}</span>{status_html}</h1>'
            f'{tags_section}{lanes_html}{actors_html}{meta_html}'
            f'<article>{body_html}</article>'
            f'{coverage_html}{related_html}{sources_html}{bl_html}{ol_html}'
        )

        html = _render_page(
            title=f"{_esc(title)} — {_esc(kb_name)} | Pyrite",
            description=_esc(description),
            og_title=f"{_esc(title)} — {_esc(kb_name)}",
            og_type="article",
            og_url=canonical_path,
            og_image="/static/favicon.svg",
            twitter_card="summary",
            extra_head=extra_head,
            canonical=canonical,
            body=body,
        )

        kb_dir = self.cache_dir / kb_name
        kb_dir.mkdir(parents=True, exist_ok=True)
        (kb_dir / f"{sanitize_filename(entry_id)}.html").write_text(html, encoding="utf-8")


def _render_designed_homepage(homepage: dict, kb_name: str, total: int, *, has_about: bool = False) -> str:
    """Render a designed homepage from a _homepage entry's structured markdown."""
    body_md = homepage.get("body") or ""
    title = homepage.get("title", kb_name)

    # Parse sections from the markdown
    sections: dict[str, str] = {}
    current_section = "_intro"
    current_lines: list[str] = []

    for line in body_md.split("\n"):
        if line.startswith("## "):
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    # --- Hero ---
    intro = sections.get("_intro", "")
    # Find first section that looks like a subtitle
    for key in sections:
        if "documenting" in key.lower() or "systematic" in key.lower():
            intro = sections[key]
            break

    hero = f'''
    <div style="text-align:center;padding:3rem 0 2.5rem 0;border-bottom:1px solid var(--border);margin-bottom:3rem">
        <h1 style="font-size:2.75rem;letter-spacing:-0.03em;margin-bottom:0.75rem;line-height:1.1">{_esc(title)}</h1>
        {f'<p style="font-size:1.125rem;color:var(--ink-soft);max-width:38rem;margin:0 auto 1.5rem auto;line-height:1.6">{_md_inline(intro)}</p>' if intro else ''}
        <div style="display:flex;justify-content:center;gap:2.5rem;margin:2rem 0">
            <div><div style="font-size:2rem;font-weight:700;color:var(--gold)">{total:,}</div><div style="font-size:0.75rem;color:var(--ink-muted);text-transform:uppercase;letter-spacing:0.08em">Events</div></div>
        </div>
        <div style="display:flex;justify-content:center;gap:0.75rem;margin-top:1.5rem">
            <a href="/viewer/" style="display:inline-flex;align-items:center;gap:0.375rem;padding:0.625rem 1.25rem;background:var(--gold);color:var(--surface);border-radius:0.5rem;font-weight:600;font-size:0.875rem;text-decoration:none">Explore the Timeline</a>
            {'<a href="/site/' + _esc(kb_name) + '/_about" style="display:inline-flex;align-items:center;gap:0.375rem;padding:0.625rem 1.25rem;border:1px solid var(--border-light);color:var(--ink-soft);border-radius:0.5rem;font-weight:500;font-size:0.875rem;text-decoration:none">About &amp; Methodology</a>' if has_about else ''}
        </div>
    </div>'''

    # --- Search ---
    search = f'''
    <div id="site-search" style="margin-bottom:3rem">
        <input type="text" placeholder="Search {total:,} events..." style="text-align:center">
        <div class="search-results entry-list" style="margin-top:0.5rem"></div>
    </div>'''

    # --- Cascade Pattern ---
    cascade_html = ""
    cascade_text = sections.get("The Cascade Pattern", "")
    if cascade_text:
        import re
        steps = re.findall(r'\d+\.\s+\*\*(.+?)\*\*\s*[—–-]\s*(.+)', cascade_text)
        if steps:
            step_cards = []
            for i, (name, desc) in enumerate(steps):
                step_cards.append(
                    f'<div style="background:var(--surface-raised);border:1px solid var(--border);border-radius:0.625rem;padding:1.25rem;position:relative">'
                    f'<div style="display:flex;align-items:center;gap:0.625rem;margin-bottom:0.5rem">'
                    f'<span style="display:inline-flex;align-items:center;justify-content:center;width:1.75rem;height:1.75rem;border-radius:50%;background:var(--gold-glow);border:1px solid var(--gold-border);color:var(--gold);font-size:0.75rem;font-weight:700;flex-shrink:0">{i+1}</span>'
                    f'<strong style="font-size:0.9375rem">{_esc(name)}</strong>'
                    f'</div>'
                    f'<p style="font-size:0.8125rem;color:var(--ink-muted);margin:0;line-height:1.5">{_esc(desc)}</p>'
                    f'</div>'
                )
            # Intro text before the numbered list
            cascade_intro = cascade_text.split("1.")[0].strip()
            cascade_html = f'''
            <section style="margin-bottom:3rem">
                <h2 style="text-align:center;margin-bottom:0.5rem">The Cascade Pattern</h2>
                {f'<p style="text-align:center;color:var(--ink-muted);margin-bottom:1.5rem;font-size:0.9375rem">{_md_inline(cascade_intro)}</p>' if cascade_intro else ''}
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(14rem,1fr));gap:0.75rem">{"".join(step_cards)}</div>
            </section>'''

    # --- Key Findings ---
    findings_html = ""
    findings_text = sections.get("Key Findings", "")
    if findings_text:
        import re
        items = re.findall(r'-\s+\*\*(.+?)\*\*:\s*(.+)', findings_text)
        if items:
            finding_cards = []
            for label, detail in items:
                finding_cards.append(
                    f'<div style="border-left:3px solid var(--gold-border);padding:0.75rem 1rem;background:var(--surface-raised);border-radius:0 0.375rem 0.375rem 0">'
                    f'<strong style="color:var(--gold);font-size:0.8125rem;display:block;margin-bottom:0.25rem">{_esc(label)}</strong>'
                    f'<span style="font-size:0.875rem;color:var(--ink-soft);line-height:1.5">{_esc(detail)}</span>'
                    f'</div>'
                )
            findings_html = f'''
            <section style="margin-bottom:3rem">
                <h2 style="margin-bottom:1rem">Key Findings</h2>
                <div style="display:grid;gap:0.75rem">{"".join(finding_cards)}</div>
            </section>'''

    # --- Data Standards ---
    standards_html = ""
    standards_text = sections.get("Data Standards", "")
    if standards_text:
        standards_html = f'''
        <section style="margin-bottom:3rem;padding:1.5rem;background:var(--surface-raised);border:1px solid var(--border);border-radius:0.625rem">
            <h2 style="font-size:1rem;margin-bottom:0.75rem">Data Standards</h2>
            <div style="font-size:0.875rem;color:var(--ink-soft);line-height:1.6">{_md_to_html(standards_text, kb_name)}</div>
        </section>'''

    # --- Explore links ---
    explore_html = ""
    explore_text = sections.get("Explore", "")
    if explore_text:
        import re
        links = re.findall(r'\[(.+?)\]\((.+?)\)\s*[—–-]\s*(.+)', explore_text)
        if links:
            link_cards = []
            for label, href, desc in links:
                link_cards.append(
                    f'<a href="{_esc(href)}" style="display:block;padding:1rem 1.25rem;border:1px solid var(--border);border-radius:0.625rem;text-decoration:none;transition:all 0.15s;background:var(--surface-raised)"'
                    f' onmouseover="this.style.borderColor=\'var(--gold-border)\';this.style.boxShadow=\'0 2px 12px rgba(201,168,76,0.1)\'"'
                    f' onmouseout="this.style.borderColor=\'var(--border)\';this.style.boxShadow=\'none\'">'
                    f'<strong style="color:var(--ink);display:block;margin-bottom:0.25rem">{_esc(label)}</strong>'
                    f'<span style="font-size:0.8125rem;color:var(--ink-muted)">{_esc(desc)}</span>'
                    f'</a>'
                )
            explore_html = f'''
            <section style="margin-bottom:3rem">
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:0.75rem">{"".join(link_cards)}</div>
            </section>'''

    # --- Contribute ---
    contrib_html = ""
    contrib_text = sections.get("Contribute", "")
    if contrib_text:
        contrib_html = '''
        <section style="text-align:center;padding:2rem 0;border-top:1px solid var(--border);margin-top:2rem">
            <h2 style="font-size:1rem;margin-bottom:0.5rem">Open Source</h2>
            <p style="font-size:0.875rem;color:var(--ink-muted);margin-bottom:1rem">Data: CC BY-SA 4.0 · Code: MIT</p>
            <a href="https://github.com/markramm/cascade-kb" style="display:inline-flex;align-items:center;gap:0.375rem;padding:0.5rem 1rem;border:1px solid var(--border-light);border-radius:0.375rem;font-size:0.8125rem;color:var(--ink-soft);text-decoration:none">View on GitHub</a>
        </section>'''

    return hero + search + cascade_html + findings_html + explore_html + standards_html + contrib_html


def _md_inline(text: str) -> str:
    """Convert inline markdown (bold, italic, links) without wrapping in paragraphs."""
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    def _safe_inline_link(m: re.Match) -> str:
        link_text = _esc(m.group(1))
        url = m.group(2).strip()
        if url.lower().startswith(("javascript:", "data:", "vbscript:")):
            return link_text
        return f'<a href="{_esc(url)}">{link_text}</a>'

    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _safe_inline_link, text)
    return text


def _esc(text: str) -> str:
    """HTML-escape text for safe insertion into HTML content and attributes."""
    if text is None:
        return ""
    return (
        str(text).replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
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

    # Markdown links [text](url) — escape text and block dangerous URLs
    def _safe_link(m: re.Match) -> str:
        text = _esc(m.group(1))
        url = m.group(2).strip()
        if url.lower().startswith(("javascript:", "data:", "vbscript:")):
            return text
        return f'<a href="{_esc(url)}">{text}</a>'

    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _safe_link, html)

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
