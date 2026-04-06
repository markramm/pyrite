---
id: search-stats-command
type: backlog_item
title: "Add pyrite search --stats or pyrite kb stats for content statistics"
kind: feature
status: proposed
priority: medium
effort: M
tags: [cli, search, ux]
---

## Problem

There is no command to get a quick overview of KB content: entry counts by type, date ranges, tag distributions. `pyrite index stats` exists but covers index health, not content statistics. The old skill documentation referenced `--stats` on search, which doesn't exist.

## Solution

Either:
- `pyrite search --stats` that shows per-KB entry counts, type breakdowns, and date ranges
- `pyrite kb stats [kb-name]` as a dedicated command

The output should be useful for answering "what do I have?" and "how much coverage do I have in this date range?"

## Workaround

`pyrite kb list` gives entry counts per KB but no type/date/tag breakdowns.
