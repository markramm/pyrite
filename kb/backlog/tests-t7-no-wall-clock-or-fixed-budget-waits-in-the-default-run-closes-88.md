---
id: tests-t7-no-wall-clock-or-fixed-budget-waits-in-the-default-run-closes-88
title: 'Tests T7: no wall-clock or fixed-budget waits in the default run (closes #88)'
type: backlog_item
tags:
- quality
- test
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: M
rank: 0
---

Source: test-architecture review 2026-09-25 (theme T7). Milestone 0.26, as the maintainer decided on 2026-09-24. Closes #88. Takes the remaining half of #102 (a caller can see that a wait timed out) and #127 (the `test_api_tiers` teardown race), and absorbs [[teardown-races-between-temporarydirectory-and-the-indexworker-thread-under-n]].

## Problem

- `tests/test_index_worker.py` has 8 sleeps, and `for _ in range(50): ... sleep(0.1)` loops whose 5 s budget falls through silently (#88).
- `IndexWorker.wait_for_idle(timeout)` (`pyrite/services/index_worker.py:48`) joins each thread with a timeout but never tells the caller it expired. So fixtures tear down under a live thread (#102, #127).
- `test_ephemeral_service.py:51` sleeps 1.1 s against a TTL of 1 s, and there is no injectable clock.
- `test_writes_never_block_on_embedding.py:161` asserts `elapsed < 2.0` on a cold subprocess import under load.
- `test_models.py:763` asserts `now() - parsed < 60`.

## Target shape

- A `wait_until(predicate, timeout)` helper that raises on expiry and reports the state it saw.
- `IndexWorker.wait_for_idle` returns a result, or raises, when it times out.
- The ephemeral TTL takes an injectable clock.
- The cold-write bound becomes a structural assertion (no torch import, which already exists) plus a `slow`-marked timing check.

## Groom 2026-09-25

**Acceptance** (verbatim from the review, plus the absorbed tickets):
1. `tests/test_index_worker.py` passes 20/20 in #88's reproducer loop at `-n 4` under load (report the loop).
2. There is no `time.sleep` in default-run tests outside an allowlist of deadline loops (rules test).
3. `wait_for_idle` timing out is visible to its caller, with a test.
4. From #102: a caller can wait for a submitted sync to complete, with a test that asserts no worker thread is alive after it returns. Shutting down the worker closes its connections deterministically.
5. From the teardown-races item: "No test made serial, no timeout widened; the fix is ordering, not waiting." `pytest tests/test_api_tiers.py tests/test_index_worker.py -n 4`, 20 consecutive runs under load, 0 errors (#127).

**Touches:**
- Existing: `tests/test_index_worker.py`, `pyrite/services/index_worker.py` (the `wait_for_idle` return value), `tests/conftest.py` (`rest_api_env` teardown uses the result), `tests/test_ephemeral_service.py`, `pyrite/services/ephemeral_service.py` (clock seam), `tests/test_writes_never_block_on_embedding.py`, `tests/test_models.py`, `tests/test_test_rules.py` (rule 4), and the `three_key_client` fixture in `tests/test_api_tiers.py`.
- New: the wait helper (`tests/_wait.py` or similar).

**Sequence:**
- After #387 (#377), which edits `pyrite/services/ephemeral_service.py`.
- After T1 (`test_writes_never_block_on_embedding.py`, and the rules file).
- After T3 (`tests/conftest.py`, `tests/test_models.py`).
- Before T4, which should use the helper; if T4 goes first, T4 adopts the helper later.
- The `tests/test_api_tiers.py` hunk is auth-adjacent. If the private security batch is still open at dispatch, check its footprint. If it touches that file, carve the hunk out and land it after the batch.

**Model:** Sonnet. **Size:** S–M. **Heavy:** yes. **Cold read:** no (small product seams, no public shape).

**Out of scope:**
- Rewriting `IndexWorker` onto an executor or futures.
- The embed queue (ADR-0035).
- Making any test serial, or `retries`.
- The world builder (T4).
