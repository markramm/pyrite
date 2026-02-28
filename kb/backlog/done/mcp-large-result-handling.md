---
id: mcp-large-result-handling
title: MCP Large Result Handling
type: backlog_item
tags:
- improvement
- mcp
kind: improvement
priority: low
effort: M
status: done
---

## Problem

When MCP tool results exceed Claude Desktop size limits, results get persisted to JSON files requiring bash pipelines to parse. This breaks the natural tool-use flow and forces agents into awkward workarounds.

## Solution (Implemented)

Server-side pagination with `limit`/`offset` params pushed down to SQL, plus `has_more` flag on all paginated responses.

### Changes

| Tool | Before | After |
|------|--------|-------|
| `kb_search` | limit only | limit + offset, has_more |
| `kb_timeline` | Python-side slice, no DB LIMIT | DB LIMIT/OFFSET, has_more |
| `kb_backlinks` | unbounded | limit + offset, has_more |
| `kb_tags` | Python-side prefix filter, limit only | DB-level prefix filter via LIKE, limit + offset, has_more |

Files modified: `pyrite/storage/queries.py`, `pyrite/services/kb_service.py`, `pyrite/server/mcp_server.py`, `tests/test_mcp_server.py`

### Additional fix: semantic search

Raised `max_distance` cutoff from 1.1 to 1.3 in `embedding_service.py` and `search_service.py`. The 1.1 threshold was too aggressive for abstract/conceptual queries whose cosine distances typically land in the 1.1-1.2 range, causing zero results.

Also built the embedding index for the production DB (`/Users/markr/kb/index.db`) which had zero embeddings despite having 4,691 entries.
