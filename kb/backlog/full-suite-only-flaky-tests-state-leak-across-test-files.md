---
id: full-suite-only-flaky-tests-state-leak-across-test-files
title: 'Full-suite-only flaky tests: state leak across test files'
type: backlog_item
tags:
- bug
- ci
- testing
importance: 5
status: proposed
priority: 8
effort: M
rank: 0
---

## Problem

Three distinct tests have been observed failing under full-suite `pytest tests/ -x` runs today while passing cleanly in isolation and in small-group runs alongside neighboring test files:

1. `tests/test_index_worker.py::TestConcurrency::test_different_kbs_get_different_jobs` -- teardown `OSError: [Errno 66] Directory not empty` (tempdir race)
2. `tests/test_review_flow_e2e.py::test_amy_edit_and_comment_merges_into_kb` -- this test has since been removed (see the Amy-edit-feature-removal commit), so it's moot going forward, but it was a real full-suite-only failure while it existed
3. `tests/test_worktree_service.py::TestGitServiceWorktree::test_worktree_add_creates_directory` -- fails under full-suite `-x` run, passes in isolation and paired with neighboring files

None reproduce in isolation. None are related to any code change in the sessions that found them -- diffs touched unrelated areas (storage, auth, plugins, CLI) each time. This strongly suggests shared/leaked state across the suite: a module-level singleton, a working-directory side effect, a tempdir cleanup race, or fixture ordering sensitivity -- not per-test bugs.

Found while fixing ci-make-green-and-load-bearing item 2 (pre-commit's pytest-check hook runs `pytest tests/ -x -q --tb=no`, which is exactly the full-suite-order-dependent scenario that surfaces these). A red `-x` hook that fails on a genuinely unrelated flaky test blocks every commit indiscriminately -- exactly the "permanently-red signal trains people to ignore it" problem ci-make-green-and-load-bearing's own problem statement describes, just at the local hook level instead of CI.

## Fix

1. Root-cause each of the (currently two, once #2 is confirmed moot) remaining flakes: bisect via `pytest --lf` / narrowing test-file pairs to find the specific state leak.
2. Once identified, the likely culprits are a tempdir not fully cleaned up before the next test's setup (worktree/git operations are prime suspects -- both known flakes involve git subprocess calls) or a monkeypatched/module-level global not reset between tests.
3. Consider `pytest-randomly` (or explicit `--randomize`) in CI to surface order-dependence proactively rather than by accident, once the known flakes are fixed -- ratchet, don't add before green.

## Acceptance criteria

- `pytest tests/ -p no:cacheprovider` (fresh run, no `-x`) is 100% green three consecutive times with no reruns.
- The two currently-known flakes (`test_index_worker.py`, `test_worktree_service.py`) each get a regression test or fix note explaining what state was leaking.
