"""Self-contained search page HTML for /site/search."""

SEARCH_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Search — Pyrite Knowledge Base</title>
<meta name="description" content="Search across all knowledge bases">
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root {
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
}
*,*::before,*::after { box-sizing: border-box; }
body {
  font-family: 'Source Serif 4', Georgia, serif;
  max-width: 52rem; margin: 0 auto; padding: 0 1.5rem;
  color: var(--ink); line-height: 1.72; font-size: 1.0625rem;
  background: var(--surface);
  -webkit-font-smoothing: antialiased;
}
a { color: var(--gold); text-decoration: none; transition: color 0.15s; }
a:hover { color: var(--gold-dim); text-decoration: underline; text-underline-offset: 2px; }
h1,h2,h3 { font-family: 'DM Sans', sans-serif; color: var(--ink); line-height: 1.25; }
h1 { font-size: 2.25rem; font-weight: 700; margin: 0 0 0.75rem 0; letter-spacing: -0.02em; }

nav.site-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1.25rem 0; margin-bottom: 2.5rem;
  border-bottom: 1px solid var(--border);
}
nav.site-header .logo {
  font-family: 'DM Sans', sans-serif; font-size: 1.125rem; font-weight: 600;
  color: var(--ink); text-decoration: none; display: flex; align-items: center; gap: 0.5rem;
}
nav.site-header .logo:hover { color: var(--ink); text-decoration: none; }
nav.site-header .logo-mark {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.75rem; height: 1.75rem; border-radius: 0.375rem;
  background: linear-gradient(135deg, var(--gold), var(--gold-dim));
  color: var(--surface); font-size: 0.75rem; font-weight: 700;
}
nav.site-header .logo-sub { font-weight: 400; color: var(--ink-muted); margin-left: 0.25rem; }
nav.site-header nav a {
  font-family: 'DM Sans', sans-serif; font-size: 0.8125rem; font-weight: 500;
  color: var(--ink-muted); margin-left: 1.5rem; text-transform: uppercase; letter-spacing: 0.06em;
}
nav.site-header nav a:hover { color: var(--ink); text-decoration: none; }

.search-input {
  width: 100%; padding: 1rem 1.25rem;
  border: 1px solid var(--border); border-radius: 0.5rem;
  font-family: 'DM Sans', sans-serif; font-size: 1.0625rem;
  background: var(--surface-raised); color: var(--ink); outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.search-input:focus {
  border-color: var(--gold-border);
  box-shadow: 0 0 0 3px rgba(201,168,76,0.1);
}
.search-input::placeholder { color: var(--ink-faint); }

.search-meta {
  font-family: 'DM Sans', sans-serif; font-size: 0.8125rem;
  color: var(--ink-faint); margin: 0.75rem 0 1.5rem 0;
}

.results { margin-top: 0.5rem; }

.result-item {
  display: block; padding: 1rem 1.25rem;
  border: 1px solid var(--border); border-radius: 0.5rem;
  margin-bottom: 0.5rem; background: var(--surface-raised);
  transition: all 0.15s; text-decoration: none;
}
.result-item:hover {
  border-color: var(--gold-border); background: var(--gold-glow);
  text-decoration: none; box-shadow: 0 1px 6px rgba(201,168,76,0.08);
}
.result-title {
  font-family: 'DM Sans', sans-serif; font-weight: 500;
  color: var(--ink); font-size: 1rem;
}
.result-meta {
  font-family: 'DM Sans', sans-serif; font-size: 0.75rem;
  color: var(--ink-muted); margin-top: 0.25rem;
  display: flex; align-items: center; gap: 0.75rem;
}
.result-snippet {
  font-size: 0.875rem; color: var(--ink-soft);
  margin-top: 0.375rem; line-height: 1.5;
}
.badge {
  display: inline-block; padding: 0.15rem 0.5rem; border-radius: 0.25rem;
  font-family: 'DM Sans', sans-serif; font-size: 0.6875rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.06em;
  background: var(--surface-overlay); color: var(--ink-muted);
}
.tag {
  display: inline-block; font-family: 'DM Sans', sans-serif;
  background: var(--gold-glow); border: 1px solid var(--gold-border);
  padding: 0.1rem 0.5rem; border-radius: 1rem;
  font-size: 0.6875rem; font-weight: 500; color: var(--gold);
}

.empty-state {
  text-align: center; padding: 3rem 1rem;
  color: var(--ink-muted); font-style: italic;
}

footer {
  margin-top: 4rem; padding: 1.5rem 0;
  border-top: 1px solid var(--border);
  text-align: center; font-family: 'DM Sans', sans-serif;
  font-size: 0.75rem; color: var(--ink-faint);
}
footer a { color: var(--ink-muted); }

@media (max-width: 640px) {
  body { font-size: 1rem; padding: 0 1rem; }
  h1 { font-size: 1.75rem; }
  nav.site-header { flex-direction: column; gap: 0.75rem; align-items: flex-start; }
  nav.site-header nav a { margin-left: 0; margin-right: 1rem; }
}
</style>
</head>
<body>
<nav class="site-header">
<a href="/site" class="logo"><span class="logo-mark">Py</span> Pyrite<span class="logo-sub">Knowledge Base</span></a>
<nav><a href="/site">Home</a><a href="/site/search">Search</a></nav>
</nav>

<h1>Search</h1>
<input class="search-input" id="q" type="text" placeholder="Search across all knowledge bases..." autofocus>
<div class="search-meta" id="meta"></div>
<div class="results" id="results"></div>

<footer>Powered by <a href="https://pyrite.wiki">Pyrite</a> &mdash; Knowledge&#8209;as&#8209;Code</footer>

<script>
(function() {
  var input = document.getElementById('q');
  var results = document.getElementById('results');
  var meta = document.getElementById('meta');
  var timer;

  // Check URL for ?q= parameter
  var params = new URLSearchParams(window.location.search);
  var initialQ = params.get('q');
  if (initialQ) {
    input.value = initialQ;
    doSearch(initialQ);
  }

  input.addEventListener('input', function() {
    clearTimeout(timer);
    var q = input.value.trim();
    if (!q) {
      results.innerHTML = '';
      meta.textContent = '';
      history.replaceState(null, '', '/site/search');
      return;
    }
    timer = setTimeout(function() { doSearch(q); }, 300);
  });

  function doSearch(q) {
    history.replaceState(null, '', '/site/search?q=' + encodeURIComponent(q));
    meta.textContent = 'Searching...';

    fetch('/api/search?q=' + encodeURIComponent(q) + '&mode=hybrid&limit=50')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var items = data.results || [];
        meta.textContent = items.length + ' result' + (items.length !== 1 ? 's' : '') + ' for "' + q + '"';

        if (!items.length) {
          results.innerHTML = '<div class="empty-state">No results found.</div>';
          return;
        }

        results.innerHTML = items.map(function(e) {
          var tags = (e.tags || []).slice(0, 3).map(function(t) {
            return '<span class="tag">' + escapeHtml(t) + '</span>';
          }).join(' ');

          var snippet = '';
          if (e.body) {
            var plain = e.body.replace(/[#*_`\\[\\]]/g, '').substring(0, 150);
            snippet = '<div class="result-snippet">' + escapeHtml(plain) + (e.body.length > 150 ? '...' : '') + '</div>';
          }

          return '<a class="result-item" href="/site/' + e.kb_name + '/' + encodeURIComponent(e.id) + '">'
            + '<div class="result-title">' + escapeHtml(e.title) + '</div>'
            + '<div class="result-meta">'
            + '<span class="badge">' + escapeHtml(e.entry_type) + '</span>'
            + '<span>' + escapeHtml(e.kb_name) + '</span>'
            + (tags ? ' ' + tags : '')
            + '</div>'
            + snippet
            + '</a>';
        }).join('');
      })
      .catch(function(err) {
        meta.textContent = 'Search failed: ' + err.message;
        results.innerHTML = '';
      });
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }
})();
</script>
</body>
</html>"""
