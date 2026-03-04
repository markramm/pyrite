---
id: kb-service-decomposition
type: backlog_item
title: "Decompose KBService god-class into focused services"
kind: improvement
status: proposed
milestone: "0.18"
priority: high
effort: L
tags: [architecture, services, reliability]
links:
- kb-service
---

# Decompose KBService god-class into focused services

## Problem

`KBService` is 1,254 lines with 45 public methods spanning 7+ responsibilities: entry CRUD, KB management, graph queries, index sync, git operations, ephemeral KB lifecycle, quota enforcement, export, orientation, and collection queries. This is a textbook god-class — wide and shallow.

Many methods are thin pass-throughs that add no value:

```python
def get_tags(self, kb_name=None, limit=100):
    return self.db.get_all_tags(kb_name)[:limit]

def get_refs_to(self, entry_id, kb_name):
    return self.db.get_refs_to(entry_id, kb_name)
```

The wide interface makes it hard for callers to understand what's important, creates excessive coupling, and makes testing unnecessarily complex.

## Solution

Extract focused services from KBService:

| New Service | Responsibility | Methods to extract |
|-------------|----------------|-------------------|
| `GraphService` | Link/backlink queries, wanted pages, graph traversal | `get_refs_to`, `get_refs_from`, `get_backlinks`, `get_outlinks`, `get_wanted_pages`, `get_graph` |
| `GitService` (exists, expand) | Git commit/push per KB | `commit_kb`, `push_kb` |
| `EphemeralKBService` | Ephemeral KB lifecycle, GC | `create_ephemeral_kb`, `gc_ephemeral_kbs` |
| `QuotaService` | Creation quotas, limit checks | `check_kb_creation_allowed`, `check_entry_creation_allowed` |
| `ExportService` | KB export to directory | `export_kb_to_directory` |

The remaining `KBService` becomes a thin coordinator for entry CRUD + KB management + index sync — its core responsibility.

## Approach

1. Extract one service at a time, starting with `GraphService` (most self-contained)
2. Each extraction: create service class, move methods, update callers (endpoints, CLI, MCP)
3. Add DI for new services in `api.py` and `mcp_server.py`
4. Keep KBService as a facade during migration (delegate to new services) to avoid big-bang refactor

## Also addresses

- `SearchService` partially duplicates `KBService` (`get_timeline`, `get_tags`, `search_by_tag`) — resolve by having endpoints use SearchService directly and removing KBService pass-throughs.

## Files likely affected

- `pyrite/services/kb_service.py` — extract methods
- `pyrite/services/graph_service.py` — new
- `pyrite/services/ephemeral_service.py` — new
- `pyrite/services/quota_service.py` — new
- `pyrite/services/export_service.py` — new
- `pyrite/server/api.py` — DI for new services
- `pyrite/server/endpoints/graph.py` — use GraphService
- `pyrite/server/endpoints/admin.py` — use ExportService
- `pyrite/server/mcp_server.py` — inject new services

## Success criteria

- KBService < 500 lines, < 20 public methods
- Each extracted service has a clear, focused interface
- No functionality regression — all existing tests pass
- New services have dedicated test files
