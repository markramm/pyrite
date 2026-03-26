---
id: fix-xss-site-cache-title
title: "Fix XSS: HTML-escape title in site cache page template"
type: backlog_item
tags: [security, xss, site-cache]
kind: bug
status: done
priority: critical
effort: S
---

## Problem

`site_cache.py:583-586` — The `title` and `og_title` template values are not HTML-escaped before insertion into `<title>{title}</title>` and `content="{og_title}"`. An entry title like `</title><script>alert(1)</script>` injects into the page.

## Fix

HTML-escape title and og_title in `_render_entry()` and `_render_kb_index()` before passing to the template. Also escape `"` in og_title to prevent attribute breakout. The `_esc()` function exists but is not used for these values.
