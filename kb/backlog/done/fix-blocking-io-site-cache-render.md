---
id: fix-blocking-io-site-cache-render
title: "Run site cache render_all() in thread pool to avoid blocking event loop"
type: backlog_item
tags: [performance, site-cache, async]
kind: bug
status: done
priority: high
effort: S
---

## Problem

`admin.py:75` — `render_all()` performs extensive filesystem I/O and many database queries synchronously. When triggered from the sync endpoint, it blocks the async event loop for potentially many seconds, starving concurrent requests.

## Fix

Run `render_all()` via `asyncio.to_thread()` or `run_in_executor()` in the sync endpoint handler.
