---
id: bug-source-citations-claimed-but-empty-on-all-event-pages
title: 'Bug: Source citations claimed but empty on all event pages'
type: backlog_item
tags:
- bug
- cascade
- site-cache
- sources
- credibility
importance: 5
kind: bug
status: todo
priority: critical
effort: M
rank: 0
---

## Problem

The landing page claims '15,500+ source citations' but every event in the exported JSON has sources: []. No event page displays any source links, footnotes, or references.

Either the citation data exists in the KB but isn't being exported, or the 15,500 number is aspirational. Either way, the gap between claim and reality is a credibility problem for a project built on verification.

## Fix

1. Check if source data exists in the KB entries (pyrite search for entries with non-empty sources)
2. If yes: fix the export pipeline to include sources
3. If no: update the landing page to remove the claim, and prioritize source data entry
4. The Source.extra round-trip fix we just shipped may be related -- were sources being silently stripped during export?

## Scope

Cascade-specific content gap, but the export pipeline is Pyrite-general.
