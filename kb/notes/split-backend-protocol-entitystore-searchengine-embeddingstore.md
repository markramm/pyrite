---
id: split-backend-protocol-entitystore-searchengine-embeddingstore
title: "Split the 39-method Backend Protocol into EntityStore, SearchEngine, EmbeddingStore"
type: backlog_item
tags: [architecture, storage, backends, postgres, sqlite, protocol, modularity, refactor]
importance: 5
kind: improvement
status: proposed
priority: high
effort: L
rank: 1400
---

## Problem

`pyrite/storage/backends/protocol.py` declares a **39-method** Backend Protocol
that every backend (SQLite, Postgres, OverlayBackend) must implement. The
Protocol confuses three responsibilities under one name:

1. **Entity CRUD**: `upsert_entry`, `get_entry`, `delete_entry`, `list_entries`,
   `count_entries`, `get_entries_for_indexing`, etc.
2. **Search**: `search`, `search_by_tag`, `search_by_date_range`,
   `search_by_tag_prefix`, `search_semantic`.
3. **Embeddings**: `upsert_embedding`, `has_embeddings`, `embedding_stats`,
   `get_embedded_rowids`, `get_entries_for_embedding`, `delete_embedding`.

Concrete consequences:

- **SQLite/Postgres divergence.** Postgres uses tsvector FTS and pgvector
  natively; SQLite uses FTS5 and has to fake parts of the embedding interface.
  Both backends must implement all 39 methods, so the faking gets buried in
  the implementation rather than acknowledged at the type level.
- **`PostgresBackend._exec` silent-`[]`-on-error bug** (already ticketed as
  `bug-postgres-backend-silent-return-empty-on-query-error`) is a *symptom* of
  the Protocol's confusion: a method that's both "entity load" and "search
  result" can't decide whether `[]` means "no rows" or "query failed."
  Audit also caught the same pattern in `_exec_one` and `_exec_scalar`
  siblings — the existing ticket understates scope.
- **ADR-0013's Phase 2 and Phase 3 are blocked.** The unified-DB-access
  decision lays out three phases (Phase 1 done: ORM writes + raw read).
  Phase 2 ("migrate service-layer `db.conn` access") and Phase 3
  ("migrate extension/plugin access") can't proceed cleanly while the
  Backend Protocol mixes write/read/embedding under one interface — the
  service layer has to be aware of all three when it should only need one.
- **Audit-flagged "three competing DB-access patterns"** (raw SQL,
  SQLAlchemy ORM, `.execute(text(...))`): the Protocol's mixed responsibility
  is what forces this. Each method picks the pattern that fits its job; with
  one Protocol, the patterns coexist.

## Solution

Split into three protocols:

```python
class EntityStore(Protocol):
    """CRUD over entries: upsert, get, delete, list."""

class SearchEngine(Protocol):
    """Lexical search: FTS, tag, date-range, prefix."""

class EmbeddingStore(Protocol):
    """Vector store: upsert/delete embeddings, semantic search, stats."""
```

SQLite and Postgres each provide all three but as separate implementations
(or as separate methods on one class that implements all three protocols —
the latter is the smaller refactor). The "three competing DB-access patterns"
debt dissolves naturally: each protocol picks one pattern.

This also closes ADR-0013's Phase 2/3: the service layer depends on the
narrow protocol it actually uses, not on a god-Backend.

### Migration order

1. Define the three protocols alongside the existing one (no breakage).
2. Re-shape `BaseBackend` to implement all three protocols as mixins.
3. Migrate service-layer call sites one protocol at a time
   (`SearchService` -> `SearchEngine`, `EmbeddingWorker` -> `EmbeddingStore`,
   `KBService` -> `EntityStore`).
4. Fix the silent-`[]`-on-error bug in `_exec` / `_exec_one` / `_exec_scalar`
   as part of the SearchEngine extraction (it's a pure-search concern there).
5. Delete the old monolithic `Backend` Protocol once all call sites are
   migrated.

## Acceptance criteria

- Three protocols defined; the existing 39-method Backend Protocol marked
  deprecated.
- SQLite and Postgres backends each pass an isolated test suite per protocol.
- `_exec` / `_exec_one` / `_exec_scalar` silent-`[]`-on-error pattern fixed
  in the migrated SearchEngine implementation (raise `StorageError` with
  context, don't return `[]`).
- ADR-0013 Phase 2 marked underway; an addendum or successor ADR records the
  Protocol split.
- No service-layer call site imports the old Backend Protocol after migration.

## Related

- [[bug-postgres-backend-silent-return-empty-on-query-error]] — symptom of
  this Protocol's confusion; absorbed into Phase 4 of this ticket.
- [[bug-collection-entries-endpoint-metadata-string-pydantic-rejection]]
  (done) — narrow fix landed at the `get_collection_entries` boundary, but
  the **broader** class of bug (raw-SQL `_exec` list paths return `metadata`
  as a JSON-encoded string instead of a dict) covers ~13 latent call sites.
  The principled fix — "all reads through this layer return parsed metadata"
  — belongs in the EntityStore spec, and this ticket should absorb the
  cleanup. Acceptance criteria below extended to make that contract explicit.
- [[implement-extension-type-protocols]] — adjacent structural-protocol work
  (at the entry-type level). This ticket is at the backend level.
- ADR-0013 (Unified Database Connection and Transaction Model) — the
  half-shipped 3-phase plan this ticket completes.
- ADR-0005 (SQLAlchemy ORM with Alembic) — relevant context for the ORM
  vs raw-SQL pattern split.
- The modularity report committed alongside this ticket.

## Acceptance criteria addition (2026-06-05)

`EntityStore` (and any shared `BaseEntityStore` mixin) MUST normalize the
shape of structured columns — at minimum `metadata` and `extra_data` —
across both the ORM single-entry path and the raw-SQL list paths. The
post-split contract: every row returned by an `EntityStore` method has
`metadata` as a parsed dict, not a JSON-encoded string. This eliminates the
divergence that produced
[[bug-collection-entries-endpoint-metadata-string-pydantic-rejection]] and
prevents the remaining ~13 latent raw-SQL list-path regressions from
surfacing one bug report at a time.
