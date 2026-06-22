---
id: postgres-backend-swallows-query-errors
title: "PostgresBackend._exec swallows result errors into empty list (silent masking)"
type: backlog_item
tags: [storage, postgres, errors, silent-data-loss, backend]
importance: 5
kind: bug
status: done
priority: medium
effort: S
rank: 0
---

## Problem

`pyrite/storage/backends/postgres_backend.py` `_exec()` (around line 90-98):

```python
def _exec(self, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    """Execute raw SQL and return all rows as list of dicts."""
    result = self._session.execute(text(sql), params or {})
    try:
        rows = result.fetchall()
        cols = result.keys()
        return [dict(zip(cols, row, strict=True)) for row in rows]
    except Exception:
        return []
```

On any failure during result iteration the method returns `[]` — silently, with
no logging and no exception chaining. A caller cannot distinguish "the query
legitimately matched zero rows" from "result handling failed." This codebase has
a documented history of silent-data-loss bugs, so this masking pattern is worth
closing.

## Scope / nuance

The `except` wraps **only** `fetchall()` / `result.keys()` / the dict
comprehension — the `self._session.execute(...)` call is *outside* the try, so a
SQL-syntax / connection error still raises normally. The masked surface is
result materialization (e.g. an unexpected row shape, a `strict=True` zip
mismatch, a driver decode error). Narrow, but real: those failures currently
read as "no rows" to every caller of the Postgres backend.

## Solution

1. Move the `try` to cover the `execute` as well (or leave execute outside if
   intentional) and, on exception, log at error level with the SQL context and
   re-raise as `StorageError(...) from e` rather than returning `[]`.
2. Audit `_exec_one()` and the other `except`/swallow sites in
   `postgres_backend.py` for the same pattern.
3. Decide the contract: callers that genuinely want "empty on error" should opt
   in explicitly; the default should surface failures.

## Acceptance criteria

- `_exec` no longer returns `[]` on an internal error — it logs and raises
  `StorageError` (chained with `from e`).
- A test injects a failing result and asserts `StorageError` is raised, not an
  empty list.
- The legitimate zero-rows path still returns `[]`.

## Related

- Commit `c348087` — the error-handling sweep that flagged this (storage layer
  was audited but this site left for a targeted fix).
- `extract-basebackend-to-deduplicate-sqlite-and-postgres-backends` (done) —
  the backend structure this lives in.
