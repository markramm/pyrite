---
id: fix-timeline-kb-filter-and-sort
type: backlog_item
title: "pyrite timeline should filter by KB and sort by date"
kind: bug
status: done
priority: high
effort: S
tags: [cli, timeline, ux]
---

## Problem

`pyrite timeline --limit 5` returns events from all KBs (including project tracker items) with no clear date sort. There's no way to say "give me the 5 most recent cascade-timeline events."

## Solution

- `pyrite timeline -k cascade-timeline --limit 5` should work
- Results should be sorted by date descending by default
- This is the most natural way to find "where did we leave off?"

## Reported By

User testing daily-capture skill with cascade-timeline KB (2026-03-31).
