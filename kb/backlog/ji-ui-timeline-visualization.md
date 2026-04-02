---
id: ji-ui-timeline-visualization
title: Interactive timeline visualization for investigations
type: backlog_item
tags:
- journalism
- investigation
- web
- frontend
- timeline
links:
- target: epic-investigation-ui-views
  relation: subtask_of
  kb: pyrite
kind: feature
status: proposed
priority: high
effort: L
---

## Problem

Investigative timelines are the core narrative structure. A journalist building a 4,000+ event timeline needs to see events visually, zoom in on periods of interest, filter by actor/tag/event type, and identify patterns and gaps.

## Scope

- Interactive timeline component (SvelteKit + Svelte 5)
- Horizontal timeline with zoomable date axis (year → month → day)
- Events displayed as cards with title, date, actors, importance indicator
- Filter sidebar: date range, actors, tags, event type (event/transaction/legal_action), importance threshold, verification status
- Color coding: by event type, importance, or verification status
- Click to expand event detail (full body, sources, linked entities)
- Gap detection: visually highlight periods with no events (may indicate missing research)
- Actor swimlanes: optional view showing events per actor as horizontal lanes
- Responsive: works on desktop and tablet

## Performance

- Must handle 4,000+ events without lag
- Virtual scrolling / viewport-based rendering
- Initial load: show recent 100 events, lazy-load on scroll/zoom
- Filter operations: <200ms response

## Acceptance Criteria

- Timeline renders 4,000+ events with smooth zoom/scroll
- Filters update the view in <200ms
- Gap detection highlights periods with no events
- Actor swimlane view shows per-actor event distribution
- Event cards link to full entry view
- Works with investigation_event, transaction, and legal_action types
