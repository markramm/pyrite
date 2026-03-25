---
id: fix-n-plus-one-site-cache
type: backlog_item
title: "Fix N+1 query pattern in site cache render_all()"
kind: bug
status: proposed
priority: high
effort: M
tags: [performance, site-cache]
epic: epic-release-readiness-review
---

## Problem

`site_cache.py:357-400` — `render_all()` issues 3 DB queries per entry (get_entry, get_backlinks, get_outlinks) inside a loop. For a 1000-entry KB, this produces ~3000 queries. Also calls `list_entries` twice (limit=1 then limit=10000 — the limit=1 call is dead code).

## Fix

Batch-load backlinks and outlinks for all entries in one query. Remove the dead limit=1 query.
