---
id: fix-red-backend-capability-tests-on-dev
title: "Fix 2 pre-existing RED tests on dev: backend capability declarations never landed"
type: backlog_item
tags: [tests, ci, backends, capabilities, r1400, tech-debt]
importance: 5
kind: bug
status: done
priority: high
effort: S
rank: 0
---

## Problem

Two tests have been failing on `dev` for some time, so the default branch's test
suite is not green:

- `tests/test_backend_capabilities.py::TestInTreeBackendDeclarations::test_sqlite_backend_declares_all_three`
- `tests/test_backend_capabilities.py::TestInTreeBackendDeclarations::test_postgres_backend_declares_all_three`

Both assert that the backend class exposes a `capabilities` ClassVar containing
`{ENTITY, SEARCH, EMBEDDING}`; `getattr(SQLiteBackend, "capabilities", set())`
returns an empty set, so the assertion fails.

A persistently-red suite is a hazard beyond the two tests: it trains everyone to
ignore failures and masks genuine regressions (this exact pair had to be ruled out
by stash-isolation while landing the unrelated search tickets this session — the
default branch should be green so that step is unnecessary).

## Root cause

The r1400 BackendCapability work landed only its first two of eight planned "fires":

- `607e916` — Add RED tests for r1400 BackendCapability declarations (fire 1/8)
- `754fe5a` — Implement BackendCapability enum + _METHOD_CAPABILITIES + dispatch helper (fire 2/8)

The RED tests (fire 1/8) and the enum/helper (fire 2/8) are committed, but the actual
`capabilities: ClassVar[set[BackendCapability]]` declaration was never added to
`SQLiteBackend` / `PostgresBackend` (the later fires stalled). So the tests are RED by
design, waiting on an implementation step that never came.

`pyrite/storage/backends/capabilities.py` already documents the exact intended
declaration:

```python
capabilities: ClassVar[set[BackendCapability]] = {
    BackendCapability.ENTITY,
    BackendCapability.SEARCH,
    BackendCapability.EMBEDDING,
}
```

## Fix

Add the `capabilities` ClassVar to `SQLiteBackend` and `PostgresBackend` (both implement
the full protocol today, so both declare all three), turning the two RED tests GREEN.
This is the small, self-contained completion of r1400 fire 3/8 — it does NOT require the
larger `[[split-backend-protocol-entitystore-searchengine-embeddingstore]]` work, which
is the eventual Option-A protocol split. Confirm `backend_declares` / the dispatch-skip
helper reads the attribute correctly once declared.

## Note: ADR number collision

`capabilities.py`'s docstring references "ADR-0028" for the r1400 design, but ADR-0028
was subsequently authored this session for the backend-agnostic query DSL
(`[[backend-agnostic-query-dsl]]`). The r1400 design was never actually written up as a
numbered ADR — fix the stale reference in the docstring (point it at the locked design
commit `3777cb5`, or write the real ADR) while here.

## Provenance

Surfaced 2026-06-23 during the search-ticket loop: the full suite was green except these
two, repeatedly requiring stash-isolation to confirm they were pre-existing and unrelated.
Filed at user request to get `dev` back to a clean suite.
