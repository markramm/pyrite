---
id: ci-parity-lint-extensions-and-enforce-the-fix-needs-a-test-rule
title: 'CI parity: lint extensions and enforce the fix-needs-a-test rule'
type: backlog_item
tags:
- ci
- contributor-experience
- programmatic-validation
importance: 5
kind: improvement
status: in_progress
priority: medium
effort: S
rank: 0
assignee: agent:pyrite-worker
---

## Problem

After [[fast-commit-hooks-full-suite-at-pre-push-ci-is-the-gate]], CI runs the
import-cycle and KB schema checks. Still missing:

- **Ruff covers `pyrite/ tests/` only.** `extensions/` had 60 lint errors (29
  I001, 19 F401, 7 F841) and 55 files that would be reformatted. The commit hook
  *does* lint extension files, so the first person to touch one inherits its
  whole lint debt in an unrelated commit (hit on 2026-09-17 while committing the
  MCP dispatch fixes — two journalism-investigation files had to be reformatted
  to get a three-line fix in).
- **`check_fix_commit_has_tests`** runs only as a local commit-msg hook. CI does
  not check PR commits, and all three outside PRs were fixes without tests.
- mypy is `continue-on-error` with 582 errors in 69 files — tracked by
  [[enforce-mypy-strict]] and the storage burn-down ticket; listed here only so
  the CI picture is in one place. Playwright likewise (its own ticket).

## Fix

One mechanical commit: `ruff check --fix` + `ruff format` over `extensions/`,
then add `extensions/` to the CI ruff step. Add a CI step that runs
`check_fix_commit_has_tests.py` over the PR's commit range.

## Acceptance

- [ ] `ruff check pyrite/ tests/ extensions/` is clean and enforced in CI.
- [ ] A `fix:` commit without a tests/ change fails CI on a PR.
- [ ] `tests/test_dev_process_config.py` pins both.

Source: 2026-09-17 project review (three read-only audits: docs/contributor, public-repo, code-health).

## Groom 2026-09-18 (architect, tick 6 — theme 6F; copied into the item at tick 10)

Model: sonnet. Cold read: no. heavy: no. Sequence: only when nothing touching
`extensions/` is in flight (true at tick 10: #140 scripts/, #145 pyrite/, #160
web/e2e, #161 git_service/repos); after #158 (ci.yml permissions) merges —
rebase onto it before editing `ci.yml`.

Touches: `extensions/**` (mechanical `ruff check --fix` + `ruff format` — 54
errors today: 29 I001, 19 F401, 7 F841 and a handful of UP/B; 46 auto-fixable,
the rest by hand with no behaviour change), `.github/workflows/ci.yml` (add
`extensions/` to the ruff step; a step running
`scripts/check_fix_commit_has_tests.py` over the PR's commit range on
`pull_request` events only), `tests/test_dev_process_config.py`.

Out of scope: mypy; the `e2e` job (H); any behaviour change inside the reformat —
the diff must be `--fix`/`format` output plus the hand fixes, each hand fix named
in the report; the `pyrite/` ruff config.
