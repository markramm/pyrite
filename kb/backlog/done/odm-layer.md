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
status: done
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
- ~~`KBService` write paths route through `DocumentManager`~~ — DONE (7 methods refactored)
- ~~At least one alternative backend passes the protocol's test suite~~ — DONE (PostgresBackend, 66/66)

## Launch Context

Phase 1 (SearchBackend protocol + SQLiteBackend) and Phase 3 (PostgresBackend) delivered in 0.10. Phase 2 (LanceDB) evaluated and rejected per [ADR-0016](../adrs/0016-lancedb-evaluation.md) — 49-280x slower across all performance metrics at Pyrite's scale. Phase 5 (DocumentManager) delivered in 0.11.

### Phase 5: DocumentManager (M) — DONE

Consolidated the repeated `repo.save() → db.register_kb() → index_mgr.index_entry()` write-path pattern from 7 KBService methods into `DocumentManager` (`pyrite/storage/document_manager.py`).

#### What was built

```python
class DocumentManager:
    def __init__(self, db: PyriteDB, index_mgr: IndexManager): ...

    def save_entry(self, entry: Entry, kb_name: str, kb_config: KBConfig) -> Path
    def delete_entry(self, entry_id: str, kb_name: str, kb_config: KBConfig) -> bool
    def index_entry(self, entry: Entry, kb_name: str, file_path: Path) -> None
```

- `save_entry`: KBRepository.save() → db.register_kb() → IndexManager.index_entry(). Returns file path.
- `delete_entry`: KBRepository.delete() → db.delete_entry(). Returns whether file was deleted.
- `index_entry`: IndexManager.index_entry() only (re-indexing from disk).

#### KBService integration

`KBService.__init__` accepts optional `doc_mgr` parameter (backward-compatible):

```python
def __init__(self, config, db, doc_mgr=None):
    self._index_mgr = IndexManager(db, config)
    self._doc_mgr = doc_mgr or DocumentManager(db, self._index_mgr)
```

7 methods refactored: `create_entry`, `bulk_create_entries`, `add_entry_from_file`, `update_entry`, `delete_entry`, `add_link`, `index_entry_from_disk`.

#### What stays as-is

- **Read paths** (`self.db.get_entry`, `list_entries`, etc.) remain on KBService/PyriteDB directly
- **`self.db`** stays on KBService — endpoints use `svc.db` for settings, starred, blocks, KB admin
- **`_index_mgr`** stays on KBService for `sync_index()` and `get_index_stats()` (admin/bulk ops)
- **`_auto_embed()`** stays in KBService (embedding is a service-layer side-effect)
- **Hook execution** stays in KBService (service-layer concern)
- **Entrypoints** (api.py, mcp_server.py, CLI) unchanged (backward-compatible constructor)

#### Tests

5 unit tests in `tests/test_document_manager.py`: save+index, KB registration, delete, index-only path, idempotency. All 1409 existing tests pass with zero regressions.

#### Design note

This phase focused on the **write path** only. Read-path delegation (routing `KBService` read calls through `DocumentManager`) was considered but deferred — the current `self.db` read calls work well and the abstraction gain doesn't justify the churn. If a future need arises (e.g., caching layer, read-through indexing), read paths can be routed through `DocumentManager` then.
