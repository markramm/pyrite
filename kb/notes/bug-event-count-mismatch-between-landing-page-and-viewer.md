---
id: bug-event-count-mismatch-between-landing-page-and-viewer
title: 'Bug: Event count mismatch between landing page and viewer'
type: backlog_item
tags:
- bug
- cascade
- site-cache
importance: 5
kind: bug
status: completed
priority: medium
effort: XS
rank: 0
---

## Problem

The capturecascade.org landing page claims '4,776 Verified Events' and '4,700+ verified events' but the viewer shows 4,529 events. The 247-event gap confuses anyone who notices.

## Fix

Either the landing page stats are stale, or some events aren't being exported to the viewer. The stats should be generated dynamically from the actual data, not hardcoded.

## Scope

Cascade-specific (hardcoded stats). But the pattern of stale stats on landing pages could be Pyrite-general if other site cache deployments use similar templates.
