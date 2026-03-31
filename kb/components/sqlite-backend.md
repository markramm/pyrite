---
id: sqlite-backend
title: SQLite Backend
type: component
kind: service
path: pyrite/storage/backends/sqlite_backend.py
owner: core
dependencies:
- pyrite.storage.backends.protocol
tags:
- core
- storage
---

Default zero-dependency storage backend implementing the SearchBackend protocol against a local SQLite file. Uses FTS5 for full-text search and optional sqlite-vec for vector search, and serves as the primary persistence layer for single-user and embedded deployments.

## Key Methods / Classes

- `upsert_entry()` — insert or replace an entry and sync all sub-tables
- `search()` — FTS5 keyword search across entry content and metadata
- `search_semantic()` — vector similarity search via sqlite-vec (optional)
- `get_backlinks()` / `get_outlinks()` — wikilink graph traversal
- `get_graph_data()` — full graph export for visualization
- `_sync_tags()`, `_sync_sources()`, `_sync_links()`, `_sync_entry_refs()`, `_sync_blocks()`, `_sync_edge_endpoints()` — internal sub-table reconciliation helpers

## Consumers

- `PyriteDB` via `ConnectionMixin` — primary consumer during all DB-backed operations

## Related

- [[search-backend-protocol]] — interface this class implements
- [[postgres-backend]] — alternative backend for multi-user deployments
- [[storage-layer]] — overall persistence architecture
