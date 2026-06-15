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

`pyrite/storage/backends/protocol.py` declares a **39-method** Backend Protocol that every backend (SQLite, Postgres, OverlayBackend) must implement. The Protocol confuses three responsibilities under one name:

1. **Entity CRUD**: `upsert_entry`, `get_entry`, `delete_entry`, `list_entries`, `count_entries`, `get_entries_for_indexing`, etc.
2. **Search**: `search`, `search_by_tag`, `search_by_date_range`, `search_by_tag_prefix`, `search_semantic`.
3. **Embeddings**: `upsert_embedding`, `has_embeddings`, `embedding_stats`, `get_embedded_rowids`, `get_entries_for_embedding`, `delete_embedding`.

Concrete consequences:

- **SQLite/Postgres divergence.** Postgres uses tsvector FTS and pgvector natively; SQLite uses FTS5 and has to fake parts of the embedding interface. Both backends must implement all 39 methods, so the faking gets buried in the implementation rather than acknowledged at the type level.
- **`PostgresBackend._exec` silent-`[]`-on-error bug** (already ticketed as `bug-postgres-backend-silent-return-empty-on-query-error`) is a *symptom* of the Protocol's confusion: a method that's both "entity load" and "search result" can't decide whether `[]` means "no rows" or "query failed." Audit also caught the same pattern in `_exec_one` and `_exec_scalar` siblings — the existing ticket understates scope.
- **ADR-0013's Phase 2 and Phase 3 are blocked.** The unified-DB-access decision lays out three phases (Phase 1 done: ORM writes + raw...

## Design (LOCKED 2026-06-15 by Mark)

**Option B chosen** — same shape as r1500's plugin solution. Option A (split into 3 protocols: `EntityStore` / `SearchEngine` / `EmbeddingStore`) is reserved as a deprecation-cycle follow-up once Option B proves the dispatch-skip wins and the `_exec` family disambiguation lands.

### BackendCapability enum (decision #1: 3 coarse members)

```python
# pyrite/storage/backends/capabilities.py
from enum import StrEnum

class BackendCapability(StrEnum):
    ENTITY    = "entity"     # CRUD on the entity table
    SEARCH    = "search"     # keyword + tag + date + semantic search
    EMBEDDING = "embedding"  # vector storage + similarity
```

Three members, not five-or-more. Sub-distinctions like "keyword vs semantic" or "FTS5 vs tsvector" are RUNTIME concerns (e.g. existing `vec_available` flag), not capability concerns. Easier to reason about; matches the r1500 Capability pattern's coarse grain.

### Class-attribute vs runtime split (decision #2)

The wrinkle r1500 didn't have: a backend's actual support depends partly on installed dependencies (sqlite-vec presence for embedding, pgvector for Postgres). The locked design keeps two questions separate:

- **Class attribute `capabilities: ClassVar[set[BackendCapability]]`** = "this backend class can in principle do X". Declared on the class definition. Read by the dispatch-skip layer.
- **Runtime checks** like `vec_available: bool` = "is the dependency installed right now in this process". Kept where it already lives in each backend.

So `SQLiteBackend.capabilities = {ENTITY, SEARCH, EMBEDDING}` always — but a call that requires embedding will still need to verify `vec_available` at runtime. Two different gates; dispatch-skip uses only the class one.

### Plugin declaration shape

```python
class SQLiteBackend:
    capabilities: ClassVar[set[BackendCapability]] = {
        BackendCapability.ENTITY,
        BackendCapability.SEARCH,
        BackendCapability.EMBEDDING,
    }

class PostgresBackend:
    capabilities: ClassVar[set[BackendCapability]] = {
        BackendCapability.ENTITY,
        BackendCapability.SEARCH,
        BackendCapability.EMBEDDING,
    }
```

Both ship with all three today; the declaration is the structural-vs-implicit win. The dispatch-skip kicks in mostly when a future backend (e.g. a read-only S3-backed entity store) opts into a subset.

### Method-to-capability map (decision #3)

Dedicated file `pyrite/storage/backends/capabilities.py` parallel to `pyrite/plugins/capabilities.py`. The 39 methods get a `_METHOD_CAPABILITIES: dict[str, BackendCapability]` table mapping each to its category. Tests assert every dispatched method is in the map (`test_every_backend_method_has_a_capability`).

### Strict-mode behavior (decision #4)

When a backend returns non-empty from a method whose capability it didn't declare:
- **Default (warn-and-skip):** WARN log with backend class + method + expected capability; treat return as empty.
- **`strict_backends=True`:** raise `BackendError`.

Mirrors `strict_plugins` toggle.

### Bundle the `_exec` silent-`[]` fix (decision #5)

`bug-postgres-backend-silent-return-empty-on-query-error` is the same root cause as the Protocol confusion — a method that straddles "entity load" and "search result" can't pick an error semantics. Once the capability gating distinguishes the two paths, `_exec` can decide based on the calling capability:

- ENTITY-path `_exec`: row-list result; `[]` means "no rows"; raise on actual SQL error.
- SEARCH-path `_exec`: same semantics; raise on actual error (don't swallow into empty).
- Each `_exec_one` / `_exec_scalar` audit followup ships in the same commit window as the capability gating.

That bundles into this r1400 arc rather than landing as a separate trailing ticket; the bug ticket retires `wont_do` with note "subsumed by r1400 fire N" when this lands.

### ADR-0013 phase coupling (decision #6)

r1400 ships first. ADR-0013's Phase 2 and Phase 3 — which the r1400 ticket calls out as blocked — pick up after r1400 closes. The unblock note goes in ADR-0013 (or its successor) once that work resumes.

### New ADR (decision #7)

New `ADR-0028: Backend Capability Declarations`. NOT an addendum to ADR-0013, which is about HOW writes go through the ORM. This decision is about WHICH methods a backend class declares it can implement — a different concern.

The new ADR mirrors the structure of ADR-0027 (per-type state machine config) and the ADR-0002 addendum (plugin capabilities): rationale, enum shape, declaration pattern, empty-set default, drift behavior, migration of in-tree backends, reservation for Option A.

## Acceptance criteria

- `pyrite.storage.backends.capabilities.BackendCapability` StrEnum with 3 members (ENTITY, SEARCH, EMBEDDING) exists.
- Both in-tree backends (SQLiteBackend, PostgresBackend) declare `capabilities: ClassVar[set[BackendCapability]]` in the same commit as the registry change.
- A backend-dispatch helper consults `_METHOD_CAPABILITIES` and `backend.capabilities` before calling each method — skipping methods whose capability is not declared.
- A backend returning non-empty from an undeclared-capability method triggers a WARNING by default; raises `BackendError` under `strict_backends=True`.
- `_exec` / `_exec_one` / `_exec_scalar` no longer swallow SQL errors into `[]` — they raise the underlying exception (or a wrapped `BackendError`) on actual failure. `[]` means "zero rows" only.
- `bug-postgres-backend-silent-return-empty-on-query-error` retires `wont_do` (subsumed) in the same commit as the `_exec` fix.
- `test_backend_capabilities_match_implementation` passes for SQLiteBackend and PostgresBackend.
- ADR-0028 filed documenting the BackendCapability enum + dispatch-skip behavior + empty-set default + reservation for Option A.

## Implementation arc

Estimated ~8 fires total:

1. RED tests for BackendCapability + dispatch-skip + declaration-mismatch (mirrors r1500 fire 1)
2. GREEN: implement the enum, the dispatch-skip helper, plus the `_METHOD_CAPABILITIES` map
3. Migrate SQLiteBackend declarations + run the test contract (atomic per r1500 pattern)
4. Migrate PostgresBackend declarations + run the test contract
5. Fix `_exec` / `_exec_one` / `_exec_scalar` error semantics (raise instead of silent `[]`)
6. Retire `bug-postgres-backend-silent-return-empty-on-query-error` (`wont_do`, subsumed-by note)
7. Write ADR-0028 + close r1400
8. (buffer) — full test suite verification + lint

L effort total. Per-fire size stays close-and-ship.

## Related

- ADR-0013 — unified DB access; Phase 2 and Phase 3 unblock once this ships
- ADR-0002 addendum (r1500 / Option B for plugins) — same pattern applied to backends
- `bug-postgres-backend-silent-return-empty-on-query-error` — subsumed by r1400 fire 5
- Future ADR for Option A — when compile-time guarantees become worth the migration churn
