---
id: fix-entry-id-path-traversal
title: "Validate entry IDs used as filenames to prevent path traversal"
type: backlog_item
tags: [security, export, site-cache]
kind: bug
priority: critical
effort: S
---

## Problem

`export_service.py:88` and `site_cache.py:595` — Entry IDs are used directly as filenames (`type_dir / f"{entry_id}.md"`) without validation. An entry ID containing `../` could write files outside the intended directory.

## Fix

Validate that entry IDs contain only safe filename characters, or sanitize by replacing path separators. Apply consistently in both export_service and site_cache.
