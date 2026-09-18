---
id: teardown-races-between-temporarydirectory-and-the-indexworker-thread-under-n
title: Teardown races between TemporaryDirectory and the IndexWorker thread under -n auto (#55 and the open-connection leak)
type: backlog_item
tags:
- quality
- testing
- flaky
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: S
rank: 0
---

## Problem

Under `pytest -n auto` on a loaded machine, `tests/test_api_tiers.py::TestTierHierarchy::test_admin_key_can_access_all_tiers` errors at teardown about one run in three (#55): the class-scoped `TemporaryDirectory` is removed while an `IndexWorker` thread is still writing into it. It sometimes drags `tests/test_index_worker.py::TestGetActiveJobs::test_active_jobs_filters` down with it. `tests-leak-open-pyritedb-connections-into-temporarydirectory-teardown` is the same family: fixtures that tear down storage while a background writer or an open connection still holds it.

This is the first thing that will make `dev` red without a code change, and two red `dev` pushes trip the conductor's circuit breaker. Retro 1 (2026-09-18) named it the week's quality theme.

## Fix

- A fixture-level rule: anything that starts an `IndexWorker` (or any background writer) must stop and join it before the directory it writes to is removed. Find every fixture that creates a `PyriteDB`/`IndexWorker` against a `TemporaryDirectory` (`grep -rn "IndexWorker\|TemporaryDirectory" tests/ extensions/*/tests`) and give them a shared teardown helper that (1) signals the worker to stop, (2) joins with a deadline, (3) closes connections, (4) only then removes the directory.
- Make the race deterministic in a test: start a worker with a slow job, tear down the fixture, assert no error and no stray files.
- Close #55; close `tests-leak-open-pyritedb-connections-into-temporarydirectory-teardown` if its cases are covered, otherwise say what is left.

## Acceptance

- `pytest tests/test_api_tiers.py tests/test_index_worker.py -n auto` 20 consecutive runs, 0 errors, on a machine under load (run the full suite in another shell at the same time).
- Full suite `-n auto` 5 consecutive runs green.
- No test made serial, no timeout widened; the fix is ordering, not waiting.

Footprint: `tests/conftest.py` (or a new `tests/_teardown.py` helper), the fixtures in `tests/test_api_tiers.py`, `tests/test_index_worker.py`, `tests/test_admin_cli.py`; no production code unless `IndexWorker` lacks a joinable stop, in which case that is a small change with its own test. Model: sonnet.
