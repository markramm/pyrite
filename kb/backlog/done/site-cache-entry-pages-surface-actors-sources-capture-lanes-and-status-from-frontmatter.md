---
id: site-cache-entry-pages-surface-actors-sources-capture-lanes-and-status-from-frontmatter
title: 'Site cache entry pages: surface actors, sources, capture lanes, and status from frontmatter'
type: backlog_item
tags:
- enhancement
- site-cache
- ux
importance: 5
kind: feature
status: completed
priority: high
effort: M
rank: 0
---

## Problem

The site cache entry renderer shows date, type badge, tags, and reading time in the metadata bar, but does not display:
- Actors/participants
- Sources (now available via batch-load fix)
- Capture lanes
- Status (confirmed, reported, etc.)
- Location
- Notes

This rich frontmatter data is the whole point of structured entries. It should be rendered prominently but kept visually separate from the body text.

## Solution

Add sections to _render_entry() in site_cache.py:
1. Actors: render as linked names (link to search filtered by actor)
2. Sources: render as a references/footnotes section with title, outlet, URL, date
3. Capture lanes: render as category badges
4. Status: render as a badge next to the type badge
5. Location: show in metadata bar

## Scope

Pyrite-general — all site cache entry pages benefit.
