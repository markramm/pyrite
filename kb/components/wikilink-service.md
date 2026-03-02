---
id: wikilink-service
title: Wikilink Service
type: component
kind: service
path: pyrite/services/wikilink_service.py
owner: core
dependencies:
- pyrite.storage
tags:
- core
- service
---

Wikilink resolution, autocomplete, and wanted-page queries. Extracted from KBService to keep it focused on CRUD. All methods are read-only and use `PyriteDB.execute_sql()` for queries.

## Key Methods

- `resolve_wikilink(text, kb_name)` — resolves a wikilink target (by ID or alias)
- `resolve_batch(texts, kb_name)` — batch resolution for multiple wikilinks
- `autocomplete(prefix, kb_name, limit)` — title/alias prefix search for editor autocomplete
- `wanted_pages(kb_name)` — entries referenced by wikilinks but not yet created

## Consumers

- REST API: `/api/entries/resolve`, `/api/entries/resolve-batch`, `/api/entries/wanted`, `/api/entries/titles`
- Web UI: editor autocomplete, wikilink pills
- MCP: `kb_backlinks` tool

## Related

- [[kb-service]] — CRUD operations
- [[storage-layer]] — SQL queries for link resolution
