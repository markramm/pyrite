---
id: investigate-and-improve-test-suite-performance
title: Investigate and Improve Test Suite Performance
type: backlog_item
tags:
- testing
- dx
- improvement
kind: improvement
status: accepted
effort: M
---

## Problem

The full test suite (2150 tests) takes ~4.5 minutes to run. While not unreasonable for the count, this slows down the development feedback loop. Every commit through pre-commit hooks runs the full suite.

## Investigation Areas

1. **Profile test runtime** — Use `pytest --durations=50` to identify the slowest tests. Are there a few outliers dominating runtime?

2. **Fixture overhead** — Many integration tests create temp directories, initialize DBs, index entries. Are fixtures being recreated unnecessarily? Could `session`-scoped fixtures help?

3. **Parallel execution** — `pytest-xdist` is already installed. Profile with `-n auto` to see if parallelism helps. Watch for test isolation issues (shared DB state, temp dirs).

4. **Test categorization** — Mark fast unit tests vs slow integration tests with pytest markers. Enable running just unit tests for quick feedback: `pytest -m "not slow"`.

5. **DB initialization** — `PyriteDB` + `IndexManager.index_all()` is called in many fixtures. Could a pre-built test DB template be copied instead of rebuilt each time?

6. **Pre-commit optimization** — Consider running only tests affected by changed files during pre-commit, with full suite in CI.

## Success Criteria

- Identify the top 20 slowest tests and their root causes
- Reduce full suite runtime by at least 30%
- Or: provide a fast subset (`pytest -m fast`) that runs in <30s for pre-commit
