---
id: a-live-server-test-harness-one-fixture-that-starts-pyrite-server-on-a-derived
title: 'A live-server test harness: one fixture that starts pyrite-server on a derived port with a scratch data dir, plus a concurrency probe helper'
type: backlog_item
tags:
- quality
- testing
- concurrency
importance: 5
status: proposed
priority: medium
rank: 0
---

## Problem

Two themes this window shipped tests that could not see the bug the cold read found, because the test exercised the *mechanism* and not the *surface the bug lives on*:

- #203 (per-request DB sessions): the worker's `TestClient` tests passed at a design stage (a thread-local session) that the live uvicorn probe showed was wrong — one anyio worker thread interleaves several requests, so one request's teardown closed another's live session. Only a real server with a real threadpool shows it. The cold read then found three more wiring defects the same way (a generator handed to the MCP mount under auth; a per-thread fallback session that never closes; singletons needing a second connection). Every one of those needed a live server or a real threadpool to observe.
- #202 (page title): nine vitest cases called the extracted module with hand-written call orders; none rendered a component, so the same-route-navigation regression was invisible until a `@testing-library/svelte` render.

The spike for #131 and the #203 cold read each hand-rolled the same thing: start `pyrite serve` on a free port against a scratch data dir, seed a few entries, fire N concurrent requests with `httpx` threads, count 5xx, kill the server. Three copies exist in the session scratchpad (`s131/probe.py`, `s131/control.py`, `rev203/*probe.py`) and none in the repo.

## Fix

One pytest fixture and one helper, in `tests/`:

- `live_server` (session- or module-scoped, opt-in via a marker so the default suite stays fast): starts `pyrite serve` as a subprocess on a derived free port with `PYRITE_DATA_DIR` pointed at a `tmp_path` data dir and a minimal config (auth off by default; an `auth_enabled` variant), waits for `/health`, yields the base URL, kills the process and asserts it exited in `finally`. Never touches `~/.pyrite`.
- `concurrent_probe(base_url, paths, concurrency, rounds)` → counts of status codes and captured tracebacks from the server log; the start-barrier + one-group-deadline discipline of `tests/test_task_claim_concurrency.py`, no wall-clock sleeps.
- Two example tests using them: the #131 read probe (0 5xx at concurrency 8 on `/api/entries`, `/api/tags`, `/api/search`) and a mixed read/write probe. These become the regression tests for #203 when it lands, replacing its in-process-only ones.
- `docs/testing.md` (or the pyrite-dev skill's testing reference) gains one paragraph: *a theme that changes request lifetime, sessions, threads or startup must enter the live-server regime — `TestClient` runs handlers on the test thread and cannot show threadpool interleaving.*

## Acceptance

- `pytest -m live_server tests/` starts one server per module, runs the two probes, leaves no process behind (asserted).
- The default `pytest tests/` (no marker) does not start a server and its wall time is unchanged (±5 s).
- The #131 read probe fails on `dev` before #203 and passes after (record both numbers).
- The fixture derives its port from the worktree like `web/e2e/ports.ts` does, so two worktrees can run it at once.

## Regimes

Cold process (no model cache — see the model-load race filed 2026-09-20); warm process; auth on and off; two fixtures in two worktrees concurrently.

**Touches** — new: `tests/live_server.py` (fixture + helper), `tests/test_live_server_probe.py`; existing: `tests/conftest.py` (register the marker), `pyproject.toml` (`markers`), `docs/testing.md`. **Sequence:** independent of #203 (it can land first; #203's redispatch then uses it). **Model:** Sonnet. **heavy:** yes (one server). **Cold read:** no. **Out of scope:** Playwright; changing any server code.
