---
type: component
title: "Storage Layer"
kind: module
path: "pyrite/storage/"
owner: "markr"
dependencies: ["sqlalchemy", "sqlite3"]
tags: [core, storage]
---

The storage layer provides SQLite-based indexing with FTS5 full-text search over git-native markdown content.

## Key Files

| File | Purpose |
|------|---------|
| `database.py` | PyriteDB: SQLAlchemy ORM + mixin-based modules (Connection, CRUD, Query, KBOps, UserOps) |
| `index.py` | IndexManager: builds/syncs index from markdown, wikilink extraction |
| `models.py` | SQLAlchemy ORM models: Entry, Link, Tag, StarredEntry, Setting |
| `queries.py` | Complex queries: graph BFS, tag tree, wanted pages |
| `repository.py` | KBRepository: reads/writes markdown files with YAML frontmatter |
| `migrations.py` | MigrationManager: custom schema versioning |

## ORM Models

- **Entry** — id, kb_name, entry_type, title, body, summary, date, importance, status, file_path, created_at, updated_at
- **Link** — source_id, source_kb, target_id, target_kb, relation, note (supports cross-KB links)
- **Tag** — entry_id, kb_name, tag (with FTS5 for prefix search)
- **StarredEntry** — entry_id, kb_name, sort_order, created_at
- **Setting** — key, value (user preferences)

## Wikilink Indexing

`IndexManager._entry_to_dict()` extracts wikilinks from entry body using `_WIKILINK_RE`:
- Pattern: `\[\[(?:([a-z0-9-]+):)?([^\]|]+?)(?:\|[^\]]+?)?\]\]`
- Supports cross-KB links: `[[kb:target]]`, `[[target]]`, `[[target|display]]`
- Group 1 = optional KB prefix, Group 2 = target ID

## Graph Queries

`get_graph_data()` in `queries.py` uses BFS from a center node with configurable depth/limit. Returns nodes (entries) and edges (links), supporting cross-KB traversal via the `target_kb` column on Link.

## Design

- Two-tier durability: markdown (git) = source of truth, SQLite = derived index
- FTS5 with BM25 ranking for keyword search
- sqlite-vec for vector/semantic search (via Embedding Service)
- Plugin tables created with IF NOT EXISTS for idempotency
- Database split into mixins to reduce merge conflicts (Wave 3B)
- Raw connection exposed for FTS5 queries that SQLAlchemy can't handle

## Related

- [ADR-0001](../adrs/0001-git-native-markdown-storage.md) — Git-native markdown storage
- [ADR-0003](../adrs/0003-two-tier-data-durability.md) — Two-tier durability model
- [Config System](config-system.md) — KB paths and configuration
- [KB Service](kb-service.md) — Service layer that orchestrates storage operations
- [Embedding Service](embedding-service.md) — Vector embeddings stored in sqlite-vec
