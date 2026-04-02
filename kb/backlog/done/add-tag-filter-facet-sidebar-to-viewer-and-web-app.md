---
id: add-tag-filter-facet-sidebar-to-viewer-and-web-app
title: Add tag filter/facet sidebar to viewer and web app
type: backlog_item
tags:
- enhancement
- web
- viewer
- tags
- filtering
importance: 5
kind: feature
status: completed
priority: high
effort: M
rank: 0
---

## Problem

No tag browsing or faceted filtering exists. The TagTree component is built but unused. Tag taxonomy is rich (6,380 unique on Cascade) but only accessible via text search.

## Solution

1. Surface top tags as clickable filter chips in the viewer sidebar
2. Allow combining multiple tag filters (AND/OR)
3. In the web app: mount TagTree component in sidebar or on a dedicated /tags route
4. Add tag facets to the entries list page sidebar

The web app already has a TagTree component ready for integration.

## Scope

Pyrite-general.
