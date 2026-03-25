---
id: fix-xss-site-cache-markdown-links
type: backlog_item
title: "Fix XSS: Sanitize URLs in markdown link rendering"
kind: bug
status: proposed
priority: critical
effort: S
tags: [security, xss, site-cache]
epic: epic-release-readiness-review
---

## Problem

`site_cache.py:749-755,792-793` — `_md_inline()` and `_md_to_html()` convert markdown links to `<a>` tags via regex without escaping URL or link text. A markdown link like `[click](javascript:alert(1))` passes through. Wikilinks are correctly escaped via `_esc()`, but standard links are not.

## Fix

Reject `javascript:` URLs in the regex replacement. HTML-escape link text. Consider using a proper markdown library (e.g., `markdown-it` or Python `markdown`) instead of hand-rolled regex.
