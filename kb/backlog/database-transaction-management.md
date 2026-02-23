---
type: backlog_item
title: "Unify Database Connection and Transaction Management"
kind: improvement
status: proposed
priority: medium
effort: L
tags: [database, architecture]
---

`PyriteDB` maintains two separate connections to the same SQLite database:
- `self.session` (SQLAlchemy ORM) for standard tables
- `self._raw_conn` (raw sqlite3) for FTS5 virtual tables, vector tables, and plugin DDL

Problems:
- Operations spanning both connections are not atomic (no shared transaction)
- No context managers around session use for proper rollback
- Plugins reach into `db._raw_conn.execute()` directly, breaking encapsulation
- ORM models exist for `Entry`, `KB`, `Tag`, `Link` but `upsert_entry()` uses raw SQL — the ORM models are mostly decorative

Options:
1. Use SQLAlchemy `text()` for all raw SQL, keeping one connection/session
2. Wrap raw connection in a helper that participates in the same transaction
3. Provide a `db.execute_raw(sql, params)` method so plugins don't touch `_raw_conn`

Also: metadata stored as JSON strings in DB loses type safety and makes querying metadata fields expensive. Consider SQLite generated columns or a separate metadata table for commonly queried fields.
