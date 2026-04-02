---
id: add-related-events-navigation-on-event-detail-pages
title: Add related events navigation on event detail pages
type: backlog_item
tags:
- enhancement
- web
- site-cache
- ux
- navigation
importance: 5
kind: feature
status: completed
priority: medium
effort: M
rank: 0
---

## Problem

Event pages are dead ends. After reading about an event, there's no link to related events sharing the same actors or high tag overlap. No prev/next navigation between chronologically adjacent events.

## Solution

1. Auto-generate 'Related events' section using tag overlap and shared actors/participants
2. Add prev/next chronological navigation links
3. Could use existing search API with participant and tag filters to find related entries
4. The web app entry detail page should also surface this (currently shows outlinks but not auto-related entries)

## Scope

Pyrite-general (related entries). The algorithm is the same regardless of KB type.
