---
id: mobile-viewer-layout-broken-sidebar-overlaps-columns-clipped
title: Mobile viewer layout broken — sidebar overlaps, columns clipped
type: backlog_item
tags:
- bug
- viewer
- mobile
- cascade
importance: 5
kind: bug
status: completed
priority: high
effort: M
rank: 0
---

## Problem

On phone width (375px), the cascade viewer has multiple layout issues:
- Sidebar overlaps the table content
- Titles are clipped mid-word
- Tags column is completely cut off (header visible, content hidden)
- Visual timeline is nearly unusable — too compressed, X-axis labels overlap
- Sidebar labels ('Timeline', 'Visual Timeline') overflow

The landing page renders fine on mobile; it's specifically the viewer app that breaks.

## Fix

Add responsive breakpoints:
- Collapse sidebar into hamburger menu on mobile
- Reformat table as cards on narrow viewports
- Provide mobile-optimized timeline view (or hide visual timeline behind 'View chart' button)

## Scope

Cascade viewer component. Decision needed: is the viewer reusable for other Pyrite sites, or cascade-only?
