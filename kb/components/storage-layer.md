---
type: component
title: "Storage Layer"
kind: module
path: "pyrite/storage/"
owner: "markr"
dependencies: ["sqlalchemy", "sqlite3", "sqlite-vec", "psycopg2 (optional)", "pgvector (optional)"]
tags: [core, storage]
---

The storage layer provides pluggable search indexing over git-native markdown content via the `SearchBackend` protocol. Two backends are implemented: SQLite (default, FTS5 + sqlite-vec) and PostgreSQL (tsvector + pgvector, for server/multi-user deployments). Both pass 66 conformance tests.

## Key Files

| File | Purpose |
|------|---------|
| `database.py` | PyriteDB: SQLAlchemy ORM + mixin-based modules (Connection, CRUD, Query, KBOps, UserOps) |
| `index.py` | IndexManager: builds/syncs index from markdown, wikilink extraction |
| `models.py` | SQLAlchemy ORM models: Entry, Link, Tag, StarredEntry, Setting |
| `queries.py` | Complex queries: graph BFS, tag tree, wanted pages |
| `repository.py` | KBRepository: reads/writes markdown files with YAML frontmatter, on-load schema migration, version stamping on save |
| `migrations.py` | MigrationManager: custom schema versioning (database DDL) |
| `backends/protocol.py` | `SearchBackend` protocol: structural interface for all index backends (ADR-0014) |
| `backends/sqlite_backend.py` | `SQLiteBackend`: wraps PyriteDB + FTS5 + sqlite-vec behind SearchBackend |
| `backends/postgres_backend.py` | `PostgresBackend`: tsvector (weighted FTS) + pgvector (HNSW cosine) |

Note: `storage/migrations.py` handles **database** schema migrations (DDL). `pyrite/migrations.py` (top-level) handles **entry** schema migrations (frontmatter transforms between type versions).

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

- Two-tier durability: markdown (git) = source of truth, search index = derived data
- **SearchBackend protocol** (structural, per ADR-0014) abstracts all index operations: upsert, delete, rebuild, FTS, semantic, hybrid search, backlinks, blocks
- **SQLiteBackend** (default): FTS5 with BM25 ranking, sqlite-vec for vector/semantic search, plugin tables with IF NOT EXISTS
- **PostgresBackend** (server): tsvector/tsquery with GIN index for FTS, pgvector HNSW for cosine similarity, configurable via `storage.backend: postgres`
- 66 conformance tests validate any SearchBackend implementation (parametrized test suite)
- LanceDB evaluated and rejected (49-66x slower indexing, 60-280x slower queries) — see [ADR-0016](../adrs/0016-lancedb-evaluation.md)
- Database split into mixins to reduce merge conflicts (Wave 3B)
- Raw connection exposed for FTS5 queries that SQLAlchemy can't handle

## Related

- [ADR-0001](../adrs/0001-git-native-markdown-storage.md) — Git-native markdown storage
- [ADR-0003](../adrs/0003-two-tier-data-durability.md) — Two-tier durability model
- [ADR-0014](../adrs/0014-structural-protocols-for-extension-types.md) — Structural protocols (SearchBackend is a protocol)
- [ADR-0016](../adrs/0016-lancedb-evaluation.md) — LanceDB evaluation and rejection
- [Config System](config-system.md) — KB paths and configuration
- [KB Service](kb-service.md) — Service layer that orchestrates storage operations
- [Embedding Service](embedding-service.md) — Vector embeddings stored in sqlite-vec / pgvector
