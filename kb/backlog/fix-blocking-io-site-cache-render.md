---
id: fix-blocking-io-site-cache-render
type: backlog_item
title: "Run site cache render_all() in thread pool to avoid blocking event loop"
kind: bug
status: proposed
priority: high
effort: S
tags: [performance, site-cache, async]
epic: epic-release-readiness-review
---

## Problem

`admin.py:75` — `render_all()` performs extensive filesystem I/O and many database queries synchronously. When triggered from the sync endpoint, it blocks the async event loop for potentially many seconds, starving concurrent requests.

## Fix

Run `render_all()` via `asyncio.to_thread()` or `run_in_executor()` in the sync endpoint handler.
