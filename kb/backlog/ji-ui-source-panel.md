---
id: ji-ui-source-panel
title: Source management panel with reliability tracking
type: backlog_item
tags:
- journalism
- investigation
- web
- frontend
- sources
links:
- target: epic-investigation-ui-views
  relation: subtask_of
  kb: pyrite
kind: feature
status: proposed
priority: medium
effort: M
---

## Problem

Source management is central to investigative journalism. Journalists need to track which sources they have, assess reliability, check URL liveness, see which claims each source supports, and identify gaps in sourcing.

## Scope

### Source List View
- All document_source entries for the investigation
- Sortable by: reliability tier, date, classification, URL status
- Filter by: reliability, classification, obtained_method, tag
- Bulk actions: check URLs, re-assess reliability

### Source Detail View
- Full source metadata: title, URL, reliability, classification, obtained date/method
- URL status: live, broken, redirect, unchecked (with last-checked timestamp)
- Evidence links: which evidence entries cite this source
- Claim chain: which claims are ultimately supported by this source
- Related sources: other sources covering the same entities/events

### Source Coverage Analysis
- Which entities have no sources?
- Which claims rely on a single source?
- Source tier distribution (pie chart: tier 1/2/3)
- Sources per claim histogram
- Temporal coverage: periods with no sources (research gaps)

### Quick Actions
- "Add source" — log a new source document with reliability assessment
- "Check URLs" — run liveness check on all/selected sources
- "Find sources" — trigger web search for entities lacking sources

## Acceptance Criteria

- Source list handles 1,000+ sources with fast filtering
- URL status indicators update after check-urls runs
- Coverage analysis identifies single-source claims and unsourced entities
- Source → claim chain traversal works in both directions
