---
type: adr
title: "Unified Database Connection and Transaction Model"
adr_number: 13
status: proposed
deciders: ["markr"]
date: "2026-02-25"
tags: [architecture, database, transactions, sqlite]
---

# ADR-0013: Unified Database Connection and Transaction Model

## Context

PyriteDB maintains two separate connections to the same SQLite database:

1. **`self.session`** (SQLAlchemy ORM) — for ORM-mapped tables (Entry, KB, Tag, Link, etc.)
2. **`self._raw_conn`** (raw sqlite3) — for FTS5 virtual tables, sqlite-vec, plugin DDL, and most queries

### Current problems

**Dual-connection non-atomicity.** Operations spanning both connections are not atomic. A write via `session.commit()` and a write via `_raw_conn.commit()` are separate transactions. If the process crashes between them, data is inconsistent.

**Raw connection leaks everywhere.** `db.conn` (a property returning `_raw_conn`) is used directly by:
- All QueryMixin methods (search, get_entry, list_entries)
- EmbeddingService (vector upserts)
- EmbeddingWorker (embed_queue table)
- Plugins via `context.db.conn.execute()`
- FTS5 and virtual table creation

The ORM session is used only by:
- StarredEntry CRUD (starred.py endpoint)
- Some CRUDMixin methods that should use raw conn instead

**No transaction scoping.** The existing `transaction()` context manager wraps the ORM session, but most operations use raw SQL. There's no equivalent for raw connection operations. Plugin hooks and service methods that compose multiple raw SQL calls have no transactional guarantee.

**ORM models are mostly decorative.** `upsert_entry()` in CRUDMixin uses raw SQL `INSERT OR REPLACE`, not the ORM. The Entry model exists but isn't used for writes. This is intentional (FTS5 triggers require raw SQL), but means the ORM session is nearly unused.

### Why not just drop SQLAlchemy?

The ORM provides:
- Schema creation via `Base.metadata.create_all()` — auto-creates all regular tables
- The `StarredEntry` model with proper relationships
- Potential future use for complex joins/queries

But the cost is two connections, dual-commit, and confusion about which to use.

## Decision

### Phase 1: Consolidate on raw connection with `execute_raw()` API

**Stop exposing `_raw_conn` directly.** Add a clean `execute_raw(sql, params)` method that:
- Wraps `_raw_conn.execute()` with error handling
- Logs slow queries in debug mode
- Returns results as list of dicts (not sqlite3.Row, which is fragile)

**Add `raw_transaction()` context manager** for raw connection operations:
```python
@contextmanager
def raw_transaction(self):
    try:
        yield self._raw_conn
        self._raw_conn.commit()
    except Exception:
        self._raw_conn.rollback()
        raise
```

**Migrate StarredEntry to raw SQL** — remove the last meaningful ORM session usage. StarredEntry is simple CRUD that doesn't need ORM.

**Deprecate `db.conn` property** — add deprecation warning, direct callers to `execute_raw()`.

### Phase 2: Clean up plugin access pattern

**Replace `context.db.conn.execute()`** in plugins with `context.db.execute_raw()`. Update the plugin protocol docs. The old pattern continues to work (deprecated) for backwards compat.

### Phase 3: Evaluate dropping SQLAlchemy

Once all runtime queries go through raw connection:
- SQLAlchemy is only used for `Base.metadata.create_all()` (schema creation)
- Could replace with explicit `CREATE TABLE IF NOT EXISTS` SQL (already done for virtual tables, migrations, plugin tables)
- Decision deferred — SQLAlchemy is low-cost at that point

## Consequences

### Positive

- **Atomic operations** — all writes go through one connection with one commit
- **Clean API** — `execute_raw()` is explicit, `db.conn` stops leaking
- **Plugin safety** — plugins can't accidentally hold raw connection references
- **Transaction support** — `raw_transaction()` gives proper rollback for multi-step operations

### Negative

- **Migration effort** — many call sites to update (QueryMixin, EmbeddingService, plugins)
- **Breaking change for plugins** — `db.conn.execute()` is deprecated (but still works)
- **Lose ORM relationships** — StarredEntry migration means manual JOIN queries

### Risks

- **SQLite WAL mode + single connection** — should handle concurrent reads fine, but write contention with background worker needs testing
- **FTS5 triggers** — depend on raw SQL `INSERT` into entry table; must verify they still fire through `execute_raw()`

## Related

- [ADR-0003: Two-Tier Data Durability](0003-two-tier-data-durability.md) — content in git, engagement in SQLite
- [ADR-0005: SQLAlchemy ORM with Alembic Migrations](0005-sqlalchemy-orm-with-alembic-migrations.md) — original ORM decision
- Backlog #40: Unify Database Connection and Transaction Management
