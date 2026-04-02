---
id: viewer-open-event-detail-in-slide-out-panel-instead-of-navigating-away
title: 'Viewer: open event detail in slide-out panel instead of navigating away'
type: backlog_item
tags:
- enhancement
- viewer
- ux
- cascade
- decision-needed
importance: 5
kind: feature
status: completed
priority: medium
effort: M
rank: 0
---

## Problem

In the cascade viewer, clicking an event title leaves the viewer entirely and navigates to the Pyrite static site page. Users lose their place in the filtered/searched timeline.

## Solution

Open a slide-out panel or modal showing the event body, tags, sources, and a 'View full page' link. Keep the viewer table/timeline visible in the background.

## Scope

Cascade viewer component. Decision needed: is this pattern worth building into the Pyrite web app entries list as well?
