---
id: mcp-bulk-create-tool
title: MCP Bulk Create Tool
type: backlog_item
tags:
- feature
- mcp
kind: feature
priority: low
effort: M
status: done
---

## Problem

Creating multiple entries via MCP requires sequential `kb_create` calls, each triggering an individual index sync and embedding generation. For batch operations (e.g., importing a set of actors or events), this is slow and produces excessive MCP round-trips.

## Solution (Implemented)

Added `kb_bulk_create` write-tier MCP tool with best-effort per-entry semantics:

```
kb_bulk_create:
  kb_name: str
  entries: array of {entry_type, title, body, date, importance, tags, metadata}
```

### Behavior

- Max 50 entries per call
- Best-effort: each entry succeeds or fails independently
- Returns per-entry results: `{created: true, entry_id}` or `{created: false, error}`
- Summary counts: `{total, created, failed, results}`
- KB registration happens once (not per-entry)
- Embedding is batched after all entries are indexed

### Files Modified

- `pyrite/services/kb_service.py` — `bulk_create_entries()` method
- `pyrite/server/mcp_server.py` — `kb_bulk_create` tool schema + `_kb_bulk_create` handler
- `tests/test_mcp_server.py` — 5 tests (happy path, partial failure, empty, read-only, over-limit)
