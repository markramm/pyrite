---
id: participants-actors-are-plain-text-not-linked-to-filtered-views
title: Participants/actors are plain text, not linked to filtered views
type: backlog_item
tags:
- enhancement
- web
- ux
- actors
importance: 5
kind: feature
status: completed
priority: high
effort: M
rank: 0
---

## Problem

In the Pyrite web app, participants on entry detail pages render as plain text divs (EntryMeta.svelte lines 53-58). Clicking a participant name should show all entries mentioning that person.

On capturecascade.org, actor names in event body text are also plain text. For investigation use cases, clicking an actor name to see all related events is essential.

7,956 unique actors tracked with avg 4.7 per event — this data is completely hidden from navigation.

## Fix

1. Make participant names in EntryMeta clickable, linking to /entries?participant=X or /search?q=participant:X
2. Add participant filter to entries list and search
3. For the cascade viewer: add actor search/browse capability

## Scope

Pyrite-general (participant linking). Cascade-specific (actor index/browse).
