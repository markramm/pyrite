---
id: add-actor-search-browse-index
title: Add actor search/browse index
type: backlog_item
tags:
- enhancement
- viewer
- actors
- cascade
- decision-needed
importance: 5
kind: feature
status: completed
priority: medium
effort: L
rank: 0
---

## Problem

Cascade tracks 7,956 unique actors averaging 4.7 per event. This data is completely hidden. No way to browse actors, see all events for an actor, or search by actor name.

## Solution

1. Actor index page showing all actors with event counts
2. Actor detail view showing all events involving that actor
3. Actor search in the viewer sidebar
4. Could leverage existing backlink indexing for string-based actor references (already implemented per backlog)

## Scope

Needs decision: is this Pyrite-general (participant/actor browse) or Cascade-specific? The underlying data model (participants field) is Pyrite-general, but the actor-centric UX is most valuable for investigation KBs.
