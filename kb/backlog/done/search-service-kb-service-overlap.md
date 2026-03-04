---
id: search-service-kb-service-overlap
type: backlog_item
title: "Resolve SearchService / KBService method duplication"
kind: improvement
status: completed
milestone: "0.18"
priority: low
effort: S
tags: [architecture, services, code-quality]
links:
- kb-service-decomposition
---

# Resolve SearchService / KBService method duplication

## Problem

Both `SearchService` and `KBService` expose identical methods that delegate to `self.db`:

| Method | KBService | SearchService |
|--------|-----------|---------------|
| `get_timeline()` | Yes | Yes |
| `get_tags()` | Yes | Yes |
| `search_by_tag()` / `search_by_tag_prefix()` | Yes | Yes |

Callers must choose which service to use for the same operation. This is confusing and violates single responsibility.

## Solution

- **SearchService owns search/query operations** — `get_timeline`, `get_tags`, `search_by_tag`, full-text search, semantic search
- **KBService owns CRUD and lifecycle** — create, update, delete, get, sync
- Remove duplicate methods from KBService
- Update endpoints/CLI/MCP to use the correct service

This should be done after or during [[kb-service-decomposition]] since the KBService methods are being extracted anyway.

## Files likely affected

- `pyrite/services/kb_service.py` — remove duplicate methods
- `pyrite/server/endpoints/tags.py` — switch to SearchService
- `pyrite/server/endpoints/timeline.py` — switch to SearchService
- `pyrite/server/mcp_server.py` — use SearchService for queries

## Success criteria

- No method exists in both KBService and SearchService
- Each query has exactly one service to call
