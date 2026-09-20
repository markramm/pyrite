---
id: one-sqlalchemy-session-shared-across-threadpool-handlers-per-request-sessions
title: 'One SQLAlchemy session shared across threadpool handlers: per-request sessions (#131)'
type: backlog_item
tags:
- bug
- server
- storage
importance: 5
status: done
priority: medium
rank: 0
assignee: agent:pyrite-worker
---

# API returns 500s under concurrent load: 'This session is provisioning a new connection; concurrent operations are not permitted'

Found while running the Playwright suite repeatedly for Package C (PR #82).

## What happens

Under parallel load the backend logs, repeatedly:

    sqlalchemy.exc.InvalidRequestError: This session is provisioning a new
    connection; concurrent operations are not permitted
    (Background on this error at: https://sqlalche.me/e/20/isce)

as `ERROR: Exception in ASGI application`. The traceback contains only framework frames (uvicorn → starlette → fastapi/routing → sqlalchemy `orm/session.py: _raise_for_prerequisite_state`), so the failure happens while a request-scoped session is being provisioned, before reaching Pyrite handler code.

The requests that hit it return errors, and the pages under test render those errors instead of their content.

## Evidence that it is load-dependent and that it causes test failures

Counting SQLAlchemy errors against total Playwright failures in the same run, same branch, same specs:

| run | InvalidRequestError count | suite failures |
|-----|---------------------------|----------------|
| a   | 0  | 8  |
| b   | 0  | 8  |
| c   | 0  | 9  |
| d   | 0  | 10 |
| e   | 2  | 12 |
| f   | 16 | 25 |

With zero backend errors the failure count sits at the known baseline of 8–10 (specs not yet rewritten by packages D/E/F/G). Every run with backend errors has strictly more failures, and the excess failures are spread across specs whose assertions are otherwise stable — including specs that pass in every clean run.

It reproduces without any other worktree running, so it is not merely machine contention; concurrency within one suite run (5 Playwright workers against one backend) is enough.

## Why it matters

This is a production-shaped bug, not a test bug: it is the API returning 500s under ordinary concurrent read load. For the e2e suite it is also a flake source that survives the Package A/B determinism work, because it makes a correct assertion fail for reasons the spec cannot control.

## Out of scope for Package C

The fix is in Python (`pyrite/server`, session/dependency wiring), which Package C's theme explicitly excludes: "If auth-enabled e2e needs a server-side change, that is a finding to report, not a change to make."

Reproduce with: run the whole Playwright suite (`cd web && npx playwright test`) a few times and grep the output for `InvalidRequestError`.


---
## Triage 2026-09-20

**State: needs a spike.** Labelling for the conductor as a spike, not `needs-design`: the open question is factual, not a maintainer's call.

This is the highest-value unclaimed bug in the set, for a reason the body's follow-up comment states plainly: **flipping `continue-on-error` off the `e2e` job (Playwright package H) cannot succeed while this is open.** It also manufactures exactly the "flaky e2e" the whole Playwright fan-out exists to eliminate — the specs that fail do so with "element(s) not found" on a page whose API call 500'd, which no spec rewrite can fix.

**Why a spike before a fix:** the report contains two *different* illegal states on the same SQLAlchemy session — "This session is provisioning a new connection; concurrent operations are not permitted" (local) and "This session is in 'prepared' state; no further SQL can be emitted within this transaction" (CI run 35324168334), plus an unexplained `IndexError: tuple index out of range` — and every traceback frame is framework code. Two illegal states on one session object points at **one session shared across concurrent requests**, but which session, and how it comes to be shared (a module-level singleton, a dependency with the wrong scope, an `async def` handler touching a sync session, a `lru_cache`d factory) is not established. A worker handed this issue as written would guess.

**The spike question, answerable in 45 minutes, read-only:** which object is shared? Read the session/engine wiring in `pyrite/server/api.py` and `pyrite/server/deps.py` (or wherever `get_db`/the SQLAlchemy `Session` dependency lives), determine the scope of every `Session`/`sessionmaker`/engine created at import time or cached, and report (a) the one that is reachable from two concurrent requests, (b) whether the endpoints touching it are `async def` (a sync session inside an async handler runs on the event loop thread and will interleave), and (c) the smallest change that gives each request its own session — with the `IndexError` either explained or explicitly listed as unexplained. **Constraint:** read-only, no server, no Playwright — the machine budget forbids it and the wiring is readable.

**Reproduction for whoever fixes it afterwards** (not for the spike): the body's own — run the Playwright suite a few times and grep for `InvalidRequestError`; it needs no second worktree, 5 workers against one backend is enough, and it reproduces on a 2-4 core CI runner.

**When it becomes a fix theme:** **opus**, **cold read: yes** (server + storage session lifecycle), **heavy: yes** for the *evidence* (a Playwright run to show the error count goes to zero — one machine slot, one at a time). Sequence it **before package H**.

## Spike 2026-09-20

**Verdict: hypothesis confirmed.** One `sqlalchemy.orm.Session` object is shared by every concurrent request. Both reported error messages *and* the unexplained `IndexError` reproduce from that one variable, and all three go to zero when each unit of work gets its own session. This is a real server bug, not a test bug. Spike branch discarded, no code changed.

### 1. Which object is shared, and where it is created

`PyriteDB` creates **exactly one** `Session` in its constructor and keeps it for the object's lifetime:

- `pyrite/storage/connection.py:57` — `self.session = Session(self.engine)`
- `pyrite/storage/connection.py:61-63` — one `self._sa_conn` / `self._raw_conn` alongside it, same lifetime
- `pyrite/storage/connection.py:41` — `connect_args={"check_same_thread": False}`, which **disables sqlite3's own cross-thread guard**. That is why the failure is a corrupted result instead of a clean `ProgrammingError`.

That one `PyriteDB` is then cached on app state and handed to every request:

- `pyrite/server/api.py:762-767` — `_app_get_db()` builds `PyriteDB` once and stores it at `application.state.pyrite_db`; every later request returns the same instance.

Everything downstream shares it by reference. `KBService`, `SearchService`, `TaskService` etc. *are* constructed per request (`api.py:173-178`, `api.py:334-339`), which makes the wiring look request-scoped — but each one wraps the same `PyriteDB`, so `self._session` in the backend is the same object in all of them:

- `pyrite/storage/connection.py:75-79` — `SQLiteBackend(session=self.session, raw_conn=self._raw_conn, ...)`
- `pyrite/storage/backends/sqlite_backend.py:40` — `self._session = session`
- `pyrite/storage/backends/postgres_backend.py:91-92` — same shape for Postgres

**Per-request DI is not the missing piece; the session's lifetime is.** The DI layer is already per-request and already correct.

### 2. Are the handlers `async def`?

**Mostly no — and that is worse here, not better.** Across `pyrite/server/endpoints/*.py`: 8 `async def` handlers vs ~117 plain `def`. Every `def` handler is run by FastAPI on an **anyio worker thread**, confirmed in the captured traceback:

```
fastapi/routing.py:354  in run_endpoint_function
    return await run_in_threadpool(dependant.call, **values)
starlette/concurrency.py:34  in run_in_threadpool
    return await anyio.to_thread.run_sync(func)
anyio/_backends/_asyncio.py:2706  in run_sync_in_worker_thread
```

So the concurrency is genuine OS-thread parallelism against one Session — the default anyio threadpool is 40 threads, so up to 40 requests can be inside the shared Session at once. With `check_same_thread=False` nothing stops them.

There is a second, distinct exposure on the **async** side: `verify_api_key` is `async def` (`pyrite/server/api.py:408`) and calls the **synchronous** `auth_service.verify_session(token)` (`api.py:436`), which issues `db.execute_sql(...)` on the shared Session **directly on the event loop thread**. That path interleaves with threadpool handlers using the same session and blocks the loop while it does. It is on the auth-enabled e2e path specifically.

### 3. Reproduction

Two experiments, both on a scratch `PYRITE_DATA_DIR` (never `~/.pyrite`), 40 seeded notes, `dev` @ 24533f4.

**(a) Over HTTP** — a live `uvicorn pyrite.server.api:app` on a free port; N threads issuing plain reads (`/api/search`, `/api/entries`, `/api/tags`):

| concurrency | requests | 200 | **500** | 500 rate |
|---|---|---|---|---|
| 8 | 96 | 83 | **9** | **9.4%** |
| 20 | 400 | 249 | **27** | **6.8%** (122 more were 429 rate-limited, not served) |

Every one of the 500s is the same server-side traceback, all framework frames until Pyrite's read path:

```
pyrite/server/endpoints/entries.py:82   in list_entries
pyrite/services/kb_service.py:821       in list_entries
pyrite/storage/crud.py:48               in list_entries
pyrite/storage/backends/base_backend.py:456  in list_entries
pyrite/storage/backends/base_backend.py:350  in _get_entry_tags
sqlalchemy/orm/query.py:2711            in all
sqlalchemy/engine/result.py:1433        in all
sqlalchemy/orm/loading.py:227           in chunks
lib/sqlalchemy/cyextension/resultproxy.pyx:54  in BaseRow.__getitem__
IndexError: tuple index out of range
```

Concurrency 8 is the important row: **5 Playwright workers plus the UI's own parallel fetches sit exactly in that band.**

**(b) The controlled A/B** — same process, same query shape as `base_backend.list_entries` + `_get_entry_tags`, 16 threads x 15 rounds = 240 units of work, **one variable changed**: whether the work uses `db.session` or its own `Session(db.engine)` that it closes.

| arm | units | ok | failures | rate |
|---|---|---|---|---|
| **A — shared `db.session`** (current code) | 240 | 109 | **131** | **54.6%** |
| **B — session per unit of work, closed** | 240 | **240** | **0** | **0%** |

Arm A's failure breakdown is the whole of this issue, from one cause:

```
114  IndexError: tuple index out of range
 15  InvalidRequestError: This session is provisioning a new connection; concurrent operations are not permitted
  2  SystemError: NULL string with positive size with NULL passed to PyUnicode_FromString
```

**This closes the two open questions in the report.** The `IndexError: tuple index out of range` is *not* a separate bug: it is SQLAlchemy's C row accessor reading a row whose cursor another thread has already advanced or replaced. The `SystemError` is a third face of the same memory-level race — further evidence that the sharing corrupts result state rather than merely erroring. The CI run's third message, `This session is in 'prepared' state`, is the same family (a second thread mid-`commit()` on the session). One cause, four surface messages.

**Reproducer scripts**: ~60 lines each, not committed (spike branch discarded). A worker can rebuild Arm A/B from the table above in ten minutes; it is the test to copy into the suite (see acceptance criteria).

### 4. Fix shape

**Smallest correct change: give each unit of work its own `Session`, and close it.** Two things matter, one of which the naive fix gets wrong:

`scoped_session` with `remove()` at request end is the conventional shape and would work, but it is scoped to the *thread*, and the anyio threadpool reuses threads across requests — so a session leaks state between unrelated requests unless `remove()` is truly guaranteed on every exit path. A FastAPI dependency with a `finally: session.close()` is both smaller and exactly right, and covers the `async def` handlers too.

**The trap, measured:** an intermediate arm that gave each thread a session but never closed it produced **26/40 `TimeoutError: QueuePool limit of size 5 overflow 10 reached`**. The default engine pool is `QueuePool(size=5, max_overflow=10)` = 15 connections, while the anyio threadpool is 40 threads. **A fix that opens per-request sessions without closing them, or without raising `pool_size`/`max_overflow` to cover the threadpool, trades 500s for timeouts.** Both halves are required.

`PyriteDB._raw_conn` (`connection.py:61-63`) is shared the same way and used by the FTS/vec paths (`sqlite_backend.py`, `virtual_tables.py`). It is *not* exercised by the reproduction above and may be safe (sqlite3 serialises internally), but it is the same lifetime bug and should be settled, not assumed.

#### Touches

Existing:
- `pyrite/storage/connection.py` — session lifetime; keep `self.session` for CLI/single-threaded callers, add a `session_scope()` / factory
- `pyrite/server/api.py` — `_app_get_db` (762-767) and/or a new per-request session dependency; `verify_api_key` (408-436)
- `pyrite/storage/backends/sqlite_backend.py`, `postgres_backend.py`, `base_backend.py`, `overlay_backend.py` — backends take a session *per call* or are constructed per request rather than caching `self._session`
- `pyrite/storage/index.py`, `crud.py`, `queries.py`, `kb_ops.py`, `user_ops.py`, `review_ops.py` — callers of `self.session`
- `pyrite/services/*.py` — `kb_service.py`, `kb_registry_service.py`, `starred_service.py`, `auth_service.py`

New:
- one test module, e.g. `tests/test_concurrent_session_isolation.py` (Arm A/B above, as a regression test)

**Scale: ~100 `.session` references across ~11 files** (`grep -rn "\.session\b" pyrite/ --include=*.py` minus auth-session noise). This is not a one-line fix; it is a session-lifetime refactor. That is why it needs the model and the cold read the triage called for.

### 5. Acceptance criteria

1. No `PyriteDB` instance hands the same `Session` object to two requests handled concurrently. Each request obtains a session at entry and closes it at exit, on **every** path including exceptions.
2. A regression test (Arm B shape, no server needed): **≥16 threads x ≥15 rounds** of the `list_entries` + `_get_entry_tags` read path against one `PyriteDB` yields **0** of `IndexError`, `InvalidRequestError`, `SystemError`, `TimeoutError`. It must fail on current `dev` (54.6% failure) and pass after. Follow `tests/test_task_claim_concurrency.py` for the start-barrier + single group deadline pattern so it is safe under `-n auto`.
3. The engine pool covers the handler concurrency: `pool_size` + `max_overflow` ≥ the anyio threadpool limit, or the threadpool is capped to the pool. Asserted in a test, not left to the default.
4. `verify_api_key` (`api.py:408`) no longer performs synchronous DB work on the event loop thread — either it becomes `def`, or the DB call moves to a threadpool, or it uses an async session. Whichever, it must not share a session with a concurrent request.
5. HTTP-level evidence: the probe in §3(a) at **concurrency 8, ≥96 requests** returns **0** 5xx. (429s are the rate limiter doing its job and do not count as failures.)
6. Single-threaded behaviour is unchanged: the CLI, `pyrite index build` and the existing suite pass. Write paths keep their transaction semantics — `ConnectionMixin.transaction()` (`connection.py:253-261`) commits/rolls back `self.session`, so its contract must be re-stated against whatever session a caller now owns.
7. `PyriteDB._raw_conn` sharing is either fixed the same way or explicitly documented as safe with the reason.
8. Postgres is not regressed: `postgres_backend.py:91-92` has the same one-session shape and must take the same lifetime treatment.

### 6. Regimes

- **SQLite** — reproduced here. Made *silent* by `check_same_thread: False` (`connection.py:41`); corrupts results rather than erroring cleanly. Pool `QueuePool(5, +10)`.
- **Postgres** — not exercised (no instance available in this box). Same one-session-per-object construction at `postgres_backend.py:91-92`, so the same bug is expected; a shared psycopg connection under concurrent use raises rather than corrupting, so the *symptom* will differ. **Unverified — flagged, not assumed.**
- **`def` handlers (~117)** — anyio threadpool, up to 40 real threads on one Session. The dominant regime; this is what the e2e suite hits.
- **`async def` handlers (8) + `verify_api_key`** — same session touched from the event loop thread, interleaving with the threadpool and blocking the loop. Second, distinct exposure, on the auth path.
- **The e2e world** — `playwright.config.ts:40,45`: `fullyParallel: true`, `workers: undefined` locally (= CPU count, 5 in the original report), `workers: 1` in CI. **`workers: 1` in CI does not make this go away** — the browser itself issues parallel `/api` fetches per page, which is why CI run 35324168334 still hit it on a 2-4 core runner.

### 7. Dispatch

- **Model: opus.** Touches `pyrite/storage/` session lifetime across ~11 files and ~100 call sites, with a transaction-semantics contract to preserve.
- **heavy: yes** — for the evidence run (one Playwright pass to show the error count reaches zero), one machine slot, one at a time.
- **Cold read: yes** — server + storage session lifecycle, exactly as triage said.

### 8. Out of scope

- Rewriting any Playwright spec (packages D/E/F/G own that).
- Flipping `continue-on-error` off the `e2e` job — that is package H, and it is what this unblocks.
- The 429s in the probe: the rate limiter working as configured, not a defect.
- Tuning the anyio threadpool for throughput beyond what criterion 3 requires.
- Any Postgres work beyond applying the same lifetime fix and not regressing it.

### 9. Should package H wait on this?

**Yes.** The triage's read is confirmed with numbers: ordinary concurrent read load returns 500s at **9.4% at concurrency 8**, and a page whose `/api` call 500s renders nothing, which a spec can only report as `element(s) not found`. Turning `continue-on-error` off before this lands would make the `e2e` job fail on a backend defect no spec can control. **Sequence this fix before package H.**

### 10. Dispatchable

Yes — acceptance criteria above are executable as written. The one genuinely open item is handed to the worker explicitly rather than left silent: **whether `_raw_conn` sharing (`connection.py:61-63`) is also unsafe** is not settled by this spike; criterion 7 requires the worker to settle it either way.
