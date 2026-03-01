---
id: odm-layer
title: "ODM Layer: Object-Document Mapper with Backend Abstraction"
type: backlog_item
tags:
- feature
- odm
- storage
- architecture
- core
kind: feature
priority: medium
effort: L
status: in_progress
links:
- schema-versioning
- postgres-storage-backend
- extension-type-protocols
- bhag-self-configuring-knowledge-infrastructure
- roadmap
---

## Problem

Pyrite stores knowledge as typed documents (markdown + YAML frontmatter) but indexes them through SQLAlchemy ORM on SQLite — a relational database. This creates an impedance mismatch: flexible frontmatter stored as JSON blobs queried via `json_extract()`, separate FTS5 virtual tables, a separate embedding pipeline, and three query systems duct-taped to a relational engine.

Multiple storage backends are supported (SQLite, PostgreSQL). Without an abstraction layer, each backend requires rewriting the service layer.

## Relationship to Schema Versioning

Schema versioning (see [[schema-versioning]]) is **decoupled and ships first** (pre-0.8). It hooks into the existing `KBRepository` load/save paths without requiring the ODM abstraction.

When the ODM lands (post-launch), schema versioning hooks relocate from `KBRepository` into `DocumentManager` — a straightforward move, not a redesign.

See [ADR-0015 addendum](../adrs/0015-odm-layer-and-schema-migration.md) for the rationale.

## Solution

Introduce a Pyrite ODM layer between the service layer (KBService, TaskService, etc.) and storage backends. Modeled on Ming/Allura's ODM from SourceForge, adapted for git-backed file storage.

See [ADR-0015](../adrs/0015-odm-layer-and-schema-migration.md) and [ODM design doc](../designs/odm-layer.md) for full details.

### Phase 1: Define interfaces, wrap existing code (M) — DONE

- Define `SearchBackend` protocol (structural, per ADR-0014) — `pyrite/storage/backends/protocol.py`
- Implement `SQLiteBackend` wrapping existing `PyriteDB`, `IndexManager`, FTS5, embedding code — `pyrite/storage/backends/sqlite_backend.py`
- 66 conformance tests validating protocol compliance
- Route search calls through `SearchBackend`
- **No behavior change** — existing tests pass, same SQLite underneath

### Phase 2: LanceDB backend (L) — REJECTED

- Implemented `LanceDBBackend` satisfying `SearchBackend` protocol (66/66 conformance tests)
- Benchmarked: 49-66x slower indexing, 60-280x slower queries, 25-54x larger disk footprint
- **Decision: No-Go** — see [ADR-0016](../adrs/0016-lancedb-evaluation.md)
- LanceDB backend code removed from codebase

### Phase 3: Postgres backend (M) — DONE

- Implemented `PostgresBackend` satisfying `SearchBackend` protocol — `pyrite/storage/backends/postgres_backend.py`
- tsvector/tsquery with GIN index for FTS, pgvector HNSW for cosine similarity
- 66/66 conformance tests passing — full parity with SQLiteBackend
- ~3x slower indexing, ~2x slower queries vs SQLite — acceptable for server deployments
- See [[postgres-storage-backend]]

## Two-Layer Storage Architecture

The ODM formalizes the split between two storage concerns:

**Application state** (relational, needs ACID): Settings, starred entries, API keys, session data. Backend: SQLite or Postgres via SQLAlchemy (existing code, minimal changes).

**Knowledge index** (document-shaped, needs search): Entry metadata, FTS index, vector embeddings, block table, backlink graph. Backend: pluggable via `SearchBackend` protocol — SQLite/FTS5 (default), Postgres/pgvector (server deployments).

## Prerequisites

- Service layer enforcement (done, #47)
- Database transaction management (done, #40)
- Unified DB connection model (done, ADR-0013)
- Schema versioning (pre-0.8, decoupled — see [[schema-versioning]])

## Success Criteria

- ~~`SearchBackend` protocol defined and documented~~ — DONE (66 conformance tests)
- ~~`SQLiteBackend` wraps existing code behind the protocol (zero behavior change)~~ — DONE
- `KBService` routes through `DocumentManager` — direct `PyriteDB` usage eliminated from services — NOT YET
- ~~At least one alternative backend passes the protocol's test suite~~ — DONE (PostgresBackend, 66/66)

## Launch Context

Phase 1 (SearchBackend protocol + SQLiteBackend) and Phase 3 (PostgresBackend) delivered in 0.10. Phase 2 (LanceDB) evaluated and rejected per [ADR-0016](../adrs/0016-lancedb-evaluation.md) — 49-280x slower across all performance metrics at Pyrite's scale.

### Phase 5: DocumentManager (M) — PLANNED

Route `KBService` through a `DocumentManager` abstraction that owns the file→index coordination pattern currently scattered across `KBService` methods.

#### What DocumentManager owns

`DocumentManager` sits between the service layer and the two storage concerns:
- **File storage**: `KBRepository` (load/save markdown files)
- **Index storage**: `SearchBackend` (upsert/delete/query the search index)

Currently `KBService` manually coordinates these two on every CRUD operation (load from repo, index via `_index_mgr`, embed via `_auto_embed`). `DocumentManager` consolidates that coordination.

#### API surface

```python
class DocumentManager:
    def __init__(self, backend: SearchBackend, config: PyriteConfig): ...

    # Write operations (file + index coordination)
    def save(self, entry: Entry, kb_config: KBConfig) -> Path
    def delete(self, entry_id: str, kb_config: KBConfig) -> bool
    def index_entry(self, entry: Entry, kb_name: str, file_path: Path) -> None

    # Read operations — file-based
    def load(self, entry_id: str, kb_config: KBConfig) -> Entry | None

    # Read operations — index-based (delegate to SearchBackend)
    def get_entry(self, entry_id: str, kb_name: str) -> dict | None
    def list_entries(self, ...) -> list[dict]
    def count_entries(self, ...) -> int
    def search(self, query: str, ...) -> list[dict]
    def get_backlinks(self, ...) -> list[dict]
    def get_outlinks(self, ...) -> list[dict]
    def get_graph_data(self, ...) -> dict
    def get_timeline(self, ...) -> list[dict]
    def get_tags(self, ...) -> list[dict]
    # ... remaining SearchBackend delegations

    # Index management
    def sync_index(self, kb_name: str | None = None) -> dict
    def get_index_stats(self) -> dict
```

#### What stays on PyriteDB

App-state operations that are NOT knowledge-index concerns stay on `PyriteDB`:
- `register_kb` / `unregister_kb` / `get_kb_stats` (KB registry — ORM table)
- `execute_sql` (raw SQL escape hatch — used for daily notes query)
- `get_entry_versions` (git-backed version history — ORM table)
- Settings CRUD (`get_setting`, `set_setting`, etc.)
- User/repo/workspace operations
- `get_tag_tree` (hierarchical tag computation — reads from index but computes tree)

#### Implementation steps

**Step 1: Create `pyrite/storage/document_manager.py`**
- Constructor takes `SearchBackend` + `PyriteConfig`
- Absorbs `IndexManager` — it becomes an internal implementation detail
- Write ops: `save()` calls `KBRepository.save()` → `IndexManager.index_entry()`
- Read ops: thin delegation to `SearchBackend` methods
- `load()` delegates to `KBRepository.load()`

**Step 2: Wire into `KBService`**
- Change `KBService.__init__(config, db)` → `KBService.__init__(config, db, doc_manager)`
- Replace `self._index_mgr.*` calls with `self._doc_manager.*`
- Replace `self.db.get_entry()`, `self.db.list_entries()`, etc. with `self._doc_manager.*`
- Keep `self.db` for app-state operations only (`register_kb`, `execute_sql`, `get_entry_versions`)

**Step 3: Update dependency injection**
- `create_app()` in `pyrite/server/api.py` creates `DocumentManager` and passes it
- CLI entry points create `DocumentManager` and pass it
- MCP server receives `DocumentManager` through its service layer

**Step 4: Wire other services**
- `SearchService`, `WikilinkService`, `EmbeddingService` — update to use `DocumentManager` where they currently access `PyriteDB` for index queries
- `QAService`, `RepoService` — check for direct `self.db` index calls

**Step 5: Tests**
- Unit tests for `DocumentManager` (mock `SearchBackend` + `KBRepository`)
- Verify all 1404 existing tests still pass (behavioral equivalence)
- No new conformance tests needed — the existing 66 backend tests validate the layer below

#### Key constraints
- **No behavior change** — pure refactor, same call paths, same results
- **Embedding coordination** moves into `DocumentManager.save()` (currently manual `_auto_embed` in KBService)
- **Hook execution** stays in `KBService` — hooks are a service-layer concern, not a storage concern
- **Schema versioning hook point**: `DocumentManager.load()` is where `_schema_version` checking will plug in when #93 lands. For now it's a straight delegation to `KBRepository.load()`
