---
id: fix-xss-site-cache-search-widget
title: "Fix XSS: Escape HTML in site cache inline search widget"
type: backlog_item
tags: [security, xss, site-cache]
kind: bug
status: done
priority: critical
effort: S
---

## Problem

`site_cache.py:284` — The inline search widget in KB index pages inserts `e.title` and `e.entry_type` directly into innerHTML without escaping. The standalone search page (`static_search_page.py`) correctly uses `escapeHtml()`, but the embedded widget does not.

## Fix

Add the same `escapeHtml()` function used in `static_search_page.py` to the inline search widget JS in `_PAGE_TEMPLATE`.
