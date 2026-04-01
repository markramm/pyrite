---
id: timeline-viewer-jump-to-date-zoom-controls-dense-period-handling
title: 'Timeline viewer: jump-to-date, zoom controls, dense period handling'
type: backlog_item
tags:
- enhancement
- viewer
- timeline
- ux
importance: 5
kind: feature
status: todo
priority: medium
effort: L
rank: 0
---

## Problem

The D3 visual timeline has several usability issues:
1. **No visible zoom/pan controls.** Hint says 'Zoom in to see details' but no buttons or instructions
2. **Massive empty space.** Timeline spans 1142-2026 but virtually all events are in 2000s. No way to jump to a date range.
3. **Dense modern period.** 2020-2026 events are packed so tightly they're unusable without zooming. The transition from bar chart overview to individual event dots is surprising for new users.
4. **Y-axis labels barely readable.** Very faint, low-contrast text.
5. **No scroll-to-date in the vertical list timeline** (web app /timeline). No way to jump to a month.

## Solution

- Add visible zoom +/- buttons and 'fit to data' button
- Add date range preset buttons ('2020s', '2025', 'All time')
- Improve label contrast
- In the web app timeline: add month navigation sidebar or jump-to-date input

## Scope

Cascade viewer (D3 visual timeline). Pyrite-general (web app /timeline page).
