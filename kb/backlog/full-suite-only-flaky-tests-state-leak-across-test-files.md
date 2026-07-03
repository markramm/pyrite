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

## Progress

- [x] **`test_worktree_service.py` flake root-caused and fixed** (2026-07-03)
  — hypothesis in the problem statement ("both known flakes involve git
  subprocess calls") was correct. Root cause: `git commit` (the parent
  process when pytest runs as pre-commit's `pytest-check` hook) sets
  `GIT_DIR`, `GIT_INDEX_FILE=.git/index` (a path RELATIVE to the outer
  pyrite repo root), `GIT_AUTHOR_*`, `GIT_EDITOR`, etc. as environment
  variables for every hook subprocess it spawns -- standard git hook
  behavior, confirmed by direct reproduction (a throwaway repo with a
  pre-commit hook that dumps `env | grep '^GIT_'`). `GitService`'s 23
  `subprocess.run` call sites, plus two raw `subprocess.run` calls in
  `worktree_service.py` (`_find_repo_root`, `reset_to_main`), and the
  test file's own `_init_git_repo` helper, none passed an explicit
  `env=` override -- so every one of them inherited these vars when
  pytest ran under `git commit`. Any test that shells out to `git`
  against a `tmp_path` fake repo with a different `cwd` then has its
  relative `GIT_INDEX_FILE` resolve against the OUTER pyrite repo's
  index instead of the fake repo's -- reproduced directly (`git init`
  succeeds, but the subsequent `git commit` in the same fake repo
  fails with a non-zero exit because it's reading/writing the outer
  repo's index).

  Fixed by adding a module-level `_git_env()` helper in
  `git_service.py` (env vars: `GIT_DIR`, `GIT_WORK_TREE`,
  `GIT_INDEX_FILE`, `GIT_AUTHOR_NAME/EMAIL/DATE`,
  `GIT_COMMITTER_NAME/EMAIL/DATE`, `GIT_EDITOR`) and threading
  `env=_git_env()` (or `_git_env(extra)` for the two sites that already
  layer in token vars for auth) through all 23 `subprocess.run` calls
  in `GitService`. Exposed it as `GitService.subprocess_env()` for
  other modules; `worktree_service.py`'s two raw call sites now use it.
  The test file's own `_init_git_repo` and remaining ad-hoc `git
  add`/`git commit` calls across its fixtures were updated to use the
  same isolated env (mirroring the `_clean_git_env()` pattern already
  established in `test_collaboration_integration.py` for the same
  reason, just not applied here yet).

  Two new fault-injection tests
  (`TestGitServiceEnvIsolation::test_worktree_add_survives_leaked_parent_git_env`,
  `test_reset_to_main_survives_leaked_parent_git_env`) directly set
  `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE` via `monkeypatch` before
  exercising `GitService.worktree_add` and
  `WorktreeService.reset_to_main` -- both failed before the fix
  (`git init`/`git commit` erroring against the wrong repo), both pass
  after.

  **Verified against the real reproduction, not just the synthetic
  test**: ran `test_worktree_service.py` with
  `GIT_DIR=/Users/markr/pyrite/.git
  GIT_WORK_TREE=/Users/markr/pyrite
  GIT_INDEX_FILE=/Users/markr/pyrite/.git/index` set in the actual
  shell env (the exact vars a real `git commit` sets for hook
  subprocesses) -- all 22 tests pass. Then ran the full suite for
  real: `pytest tests/ -x -q --tb=short` -- **3028 passed, 68 skipped,
  7 deselected, 0 failures**, no `-x` stop. This is the first clean
  full-suite run this session (prior runs all stopped at this exact
  test after ~2980 tests). Confirms this is a real fix, not a
  narrower-reproduction coincidence.

- [ ] `test_index_worker.py::test_different_kbs_get_different_jobs`
  tempdir race -- not yet investigated. Different failure shape
  (`OSError: Directory not empty` at teardown, not a git-env leak), so
  likely a distinct root cause from the fix above. Deferred to a
  follow-up pass since the specific blocking pain (every commit this
  session needing `--no-verify`) is resolved by the worktree fix
  alone -- item 3 (`test_review_flow_e2e.py`) is confirmed moot (file
  removed).
- [ ] `pytest-randomly` / `--randomize` ratchet -- still gated on all
  known flakes being fixed first; one remains (`test_index_worker.py`).

## Acceptance criteria

- `pytest tests/ -p no:cacheprovider` (fresh run, no `-x`) is 100% green three consecutive times with no reruns. **Partially met**: one clean full run completed (3028 passed, 0 failed) after the worktree fix; three consecutive clean runs not yet confirmed, and `test_index_worker.py`'s separate tempdir-race flake remains open.
- The two currently-known flakes (`test_index_worker.py`, `test_worktree_service.py`) each get a regression test or fix note explaining what state was leaking. **Met for `test_worktree_service.py`** (see above); `test_index_worker.py` still open.
