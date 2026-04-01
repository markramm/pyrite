---
id: consider-paginating-timeline-json-api-for-viewer-performance
title: Consider paginating timeline.json API for viewer performance
type: backlog_item
tags:
- enhancement
- viewer
- performance
- cascade
- decision-needed
importance: 5
kind: feature
status: todo
priority: low
effort: M
rank: 0
---

## Problem

The viewer loads the entire 14.4MB timeline.json file (4,529 events with full body text) on first load. While it caches well after that, the initial load is heavy. The viewer already paginates display to 25 events per page.

## Solution

Paginate the API to match the display pagination. Load event bodies on demand when expanded or viewed. The initial payload could be title/date/tags/actors only, with body fetched on click.

## Scope

Cascade viewer. Decision needed: does this need to be a Pyrite API change, or just a viewer-side optimization of the export format?
