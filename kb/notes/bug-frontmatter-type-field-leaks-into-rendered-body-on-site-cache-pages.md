---
id: bug-frontmatter-type-field-leaks-into-rendered-body-on-site-cache-pages
title: 'Bug: Frontmatter type field leaks into rendered body on site cache pages'
type: backlog_item
tags:
- bug
- site-cache
- export
- critical
importance: 5
kind: bug
status: completed
priority: critical
effort: S
rank: 0
---

## Status

Investigation complete. The DB body content is clean (0 of 4,596 entries have type: in body). The bug exists only on the deployed site from a stale render. A fresh re-render with the current code will fix it.

## Root Cause

The live site at capturecascade.org was rendered with an older version of the code that included frontmatter fields in the body output. The current site_cache.py reads body from the DB (which is clean). No code fix needed — just a re-deploy.

## Fix

Re-render the site cache: POST /api/admin/site/render (no CLI command exists for this yet).

## Related

Consider adding a pyrite site-cache render CLI command for easier deployment.
