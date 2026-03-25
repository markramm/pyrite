---
id: fix-entry-id-path-traversal
type: backlog_item
title: "Validate entry IDs used as filenames to prevent path traversal"
kind: bug
status: proposed
priority: high
effort: S
tags: [security, export, site-cache]
epic: epic-release-readiness-review
---

## Problem

`export_service.py:88` and `site_cache.py:595` — Entry IDs are used directly as filenames (`type_dir / f"{entry_id}.md"`) without validation. An entry ID containing `../` could write files outside the intended directory.

## Fix

Validate that entry IDs contain only safe filename characters, or sanitize by replacing path separators. Apply consistently in both export_service and site_cache.
