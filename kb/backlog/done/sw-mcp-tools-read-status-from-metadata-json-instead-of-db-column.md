---
id: sw-mcp-tools-read-status-from-metadata-json-instead-of-db-column
title: sw_* MCP tools read status from metadata JSON instead of DB column
type: backlog_item
tags:
- extension:software-kb
- bug
- mcp
- software
- kanban
kind: bug
status: completed
priority: high
effort: S
---

## Problem

The sw_* MCP tool handlers (_mcp_board, _mcp_backlog, _mcp_pull_next, _mcp_review_queue, etc.) all read status from the metadata JSON blob:

    status = meta.get("status", "proposed")

But the DB stores status in a dedicated `status` column. The metadata blob often does not contain status at all — it only has kind, effort, and other extension-specific fields.

The CLI (cli.py) does it correctly with a column-first fallback:

    r.get("status") or r["_meta"].get("status", "proposed")

## Impact

- `sw_board` shows 0 in-progress items when there are actually 3
- `sw_pull_next` may recommend already-claimed items
- `sw_backlog --status in_progress` (MCP) returns wrong results
- `sw_review_queue` may miss items in review status

## Fix

Every handler that reads status from metadata should use column-first fallback:

    status = row.get("status") or meta.get("status", "proposed")

Same pattern for priority and assignee where applicable. Affects: _mcp_backlog, _mcp_board, _mcp_pull_next, _mcp_review_queue, _mcp_context_for_item, _mcp_claim, _mcp_submit, _mcp_review.
