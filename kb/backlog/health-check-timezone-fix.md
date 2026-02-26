---
id: health-check-timezone-fix
title: "Health Check Timezone False Positives"
type: backlog_item
kind: bug
status: done
priority: low
effort: S
tags: [bug, indexing, storage]
---

# Health Check Timezone False Positives

## Problem

`pyrite index health` reports false "stale" entries because `IndexManager.check_health()` (and `sync_incremental()`) compared `file_mtime` (local timezone via `datetime.fromtimestamp()`) with `indexed_at` (UTC from SQLite's `CURRENT_TIMESTAMP`). In timezones with positive UTC offsets, every entry appears stale.

## Fix

- Use `datetime.fromtimestamp(st_mtime, tz=UTC)` for file mtimes
- Added `_parse_indexed_at()` helper that normalizes `indexed_at` strings to UTC-aware datetimes
- Fixed in both `check_health()` and `sync_incremental()` in `pyrite/storage/index.py`

## Test

`tests/test_storage.py::TestIndexManager::test_check_health_no_false_stale` — verifies no false stale entries immediately after indexing.
