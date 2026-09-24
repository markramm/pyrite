/* Pyrite /site page behaviour. Served from /site/_static/site.js: the /site
   Content-Security-Policy allows scripts from 'self' only, never inline. */
(function() {
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  /* Search widget */
  var s = document.getElementById('site-search');
  if (s) {
    var i = s.querySelector('input'), r = s.querySelector('.search-results'), t;
    if (i && r) i.addEventListener('input', function() {
      clearTimeout(t); var q = i.value.trim();
      if (!q) { r.innerHTML = ''; return; }
      t = setTimeout(function() {
        fetch('/api/search?q=' + encodeURIComponent(q) + '&mode=hybrid&limit=20')
          .then(function(x) { return x.json(); })
          .then(function(d) {
            r.innerHTML = (d.results || []).map(function(e) {
              var humanType = (e.entry_type || '').replace(/_/g, ' ').replace(/-/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); });
              return '<a href="/site/' + esc(e.kb_name) + '/' + encodeURIComponent(e.id) + '">'
                + '<strong>' + esc(e.title) + '</strong><span class="badge">' + esc(humanType) + '</span></a>';
            }).join('');
          });
      }, 300);
    });
  }

  /* Heading anchors + TOC generation */
  var article = document.querySelector('article');
  if (article) {
    var headings = article.querySelectorAll('h2, h3');
    var tocItems = [];
    headings.forEach(function(h, idx) {
      var id = h.textContent.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'section-' + idx;
      h.id = id;
      var a = document.createElement('a'); a.className = 'anchor'; a.href = '#' + id; a.textContent = '#';
      a.setAttribute('aria-label', 'Link to this section');
      h.insertBefore(a, h.firstChild);
      tocItems.push({ id: id, text: h.textContent.replace(/^#\s*/, ''), level: h.tagName });
    });
    if (tocItems.length >= 3) {
      var toc = document.createElement('div'); toc.className = 'toc';
      var title = document.createElement('div'); title.className = 'toc-title'; title.textContent = 'Contents';
      var ol = document.createElement('ol');
      tocItems.forEach(function(item) {
        var li = document.createElement('li');
        if (item.level === 'H3') li.style.marginLeft = '1rem';
        /* textContent, not innerHTML: heading text is decoded entry content */
        var link = document.createElement('a'); link.href = '#' + item.id; link.textContent = item.text;
        li.appendChild(link);
        ol.appendChild(li);
      });
      toc.appendChild(title); toc.appendChild(ol);
      article.insertBefore(toc, article.firstChild);
    }
  }

  /* Back to top */
  var btt = document.getElementById('btt');
  if (btt) {
    window.addEventListener('scroll', function() {
      btt.classList.toggle('visible', window.scrollY > 400);
    });
    btt.addEventListener('click', function() { window.scrollTo({ top: 0, behavior: 'smooth' }); });
  }

  /* Smooth scroll for anchor links */
  document.querySelectorAll('a[href^="#"]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var target = document.querySelector(a.getAttribute('href'));
      if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
  });
})();
