---
id: add-importance-status-and-participant-filters-to-entries-list
title: Add importance, status, and participant filters to entries list
type: backlog_item
tags:
- enhancement
- web
- filtering
- ux
importance: 5
kind: feature
status: todo
priority: medium
effort: M
rank: 0
---

## Problem

The entries list page (/entries) only has type filter, sort, and tag filter (via URL param). Missing:
- Importance filter (only timeline has this)
- Status filter (visible on cards but not filterable)
- Participant/actor filter
- Combined filtering UI

Each page implements its own ad-hoc filter bar. No reusable filter component.

## Solution

1. Add importance range filter to entries list
2. Add status dropdown filter
3. Add participant text filter
4. Consider extracting a reusable FilterBar component shared across entries, timeline, and search

## Scope

Pyrite-general.
