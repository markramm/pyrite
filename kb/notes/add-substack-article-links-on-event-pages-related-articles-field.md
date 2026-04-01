---
id: add-substack-article-links-on-event-pages-related-articles-field
title: Add Substack article links on event pages (related_articles field)
type: backlog_item
tags:
- enhancement
- cascade
- substack
- content
importance: 5
kind: feature
status: todo
priority: high
effort: M
rank: 0
---

## Problem

When a timeline event corresponds to a RAMM Substack article (e.g. Bovino events to 'Border Patrol: A Criminal Organization', detention events to 'After the Arrest' series), the event page should link to it. This is described as a major Cascade feature but currently doesn't exist.

## Solution

1. Add a related_articles field to event entries (list of URLs or entry refs)
2. Render 'Read the investigation' links on event pages
3. Could use the existing links/outlinks system with a 'written_about_in' relationship type

## Scope

Cascade-specific feature, but the underlying 'related external content' pattern could be Pyrite-general (any KB might want to link entries to external articles).
