---
id: tags-not-clickable-in-viewer-timeline-or-search-results
title: Tags not clickable in viewer, timeline, or search results
type: backlog_item
tags:
- enhancement
- web
- tags
- ux
importance: 5
kind: bug
status: todo
priority: high
effort: S
rank: 0
---

## Problem

Tags appear in three places where they are not clickable:
1. **Viewer table** (capturecascade.org) — tags are plain spans, no click handler
2. **Timeline page** (web app, /timeline) — lines 183-187, tags are plain spans
3. **Search results** (web app, /search) — lines 401-406, tags are plain spans

Meanwhile tags ARE clickable on: entry detail metadata sidebar, entry cards, overview page, orient page. The TagBadge component supports link mode already.

The tag taxonomy is remarkably rich (6,380 unique tags on Cascade) and completely inaccessible except through the search box.

## Fix

Replace plain span tags with TagBadge components in link mode (href to /entries?tag=X) on:
- Search results page
- Timeline page
- Viewer table (cascade-specific, but same pattern)

Also: the +N overflow indicator should expand on click/hover to show hidden tags.

## Scope

Pyrite-general (web app timeline + search). Plus cascade viewer.
