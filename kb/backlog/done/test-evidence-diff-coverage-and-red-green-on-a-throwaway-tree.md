---
id: test-evidence-diff-coverage-and-red-green-on-a-throwaway-tree
title: "Test evidence: diff coverage, plus red-green on a throwaway tree (verify-red redesign)"
type: backlog_item
tags:
- quality
- test
- process
kind: tech_debt
status: done
assignee: agent:pyrite-worker
priority: high
effort: L
milestone: "0.26"
---

## Why
Approved by the maintainer on 2026-09-25. It replaces PR #374 and absorbs #368.

The value of red-green is evidence the author didn't write that a PR's tests notice its change. That matters most for AI workers, whose reports are model output, and for outside contributors: #371's table showed three contributor tests failing on real assertions against dev.

Almost all the cost has gone into reverting the fix *in the developer's tree* and guaranteeing it is restored: signal handling, retries, a journal, directory bookkeeping. That is about 980 lines of driver and about 1,900 lines of tests, and it took #357's three rounds, #368 and #374's two rounds. Two records of state kept disagreeing about when the job was done, and each fix added another. CI never needed any of it, because a CI checkout is thrown away anyway.

Meanwhile the output has been noise nobody acts on: batch 2 printed about 300 "passes without the fix" rows and T1 about 140, mostly deliberate negative controls.

Each layer answers a question the others don't:
1. **Diff coverage:** is every changed line run by a test? It is cheap and can gate. Its blind spot is code that runs but whose result no test checks.
2. **Red-green:** do the new tests notice the change as a whole?
3. **Per-hunk revert** (phase 2, separate item): does each changed hunk have a test that notices it?

## Acceptance
1. **Never modify the developer's tree.** The runner works only in a throwaway checkout: the CI job's own checkout, or locally a `git worktree add --detach` under `$TMPDIR` with the PR's test-side files overlaid, including uncommitted ones. It runs the new tests with the fix, reverts the code, and runs them again without it. Nothing is restored; cleanup is removing the throwaway tree, and a later run prunes stale ones.
   Test: a run killed with SIGKILL leaves the developer's `git status` byte-identical.
   The signal handlers, retry loop, journal, directory bookkeeping and symlink refusal are deleted.
2. **Kept:** the check that the tests import the tree under test (#189); `PYTHONDONTWRITEBYTECODE`; base = merge-base; formatting-only test edits are ignored.
3. **Scope:** report only the tests the PR adds or edits. Pre-existing tests are a count, not rows. `@pytest.mark.control` declares a deliberate negative control, which is expected to pass without the fix and is not warned about.
4. **One summary line**, e.g. `verify-red: 3 red · 0 import-only · 0 unexpected pass · 1 n/a`, in the step summary. The table lists only the tests that are not red.
5. **Import-only reds are classified by structure, never traceback text:**
   - collection fails without the fix, or
   - the failure names an identifier the PR adds (from an AST diff of base vs head).

   Test: it works under the repo's own `--tb=short`.
6. **Diff coverage in the test job:** `pytest --cov` on test (3.12), then `diff-cover coverage.xml --compare-branch=<base> --fail-under=80`. Advisory at first: it reports but does not fail `gate`. The summary shows the uncovered changed lines.
7. **One owner:** the CI `verify-red` job. `scripts/verify-red.sh` becomes a thin local entry point into the same code path. The skills (`pyrite-conductor/review.md`, `pyrite-dev`) change so that:
   - the conductor reads the CI result and does not re-run it locally;
   - a worker runs it once before reporting and pastes the summary line, instead of prose claims like "RED before each fix".
8. **Measurement for the gate decision:** each PR's verdicts and diff-coverage percentage go to a small JSON artifact. After about 10 PRs, the maintainer decides on gating: diff coverage ≥ N, and for PRs with a `fix:` commit at least one real red, with a `verify-red: n/a` label and a reason as the escape (for environment-dependent bugs like #373).
9. The guards rule (#360) applies to the new runner itself.

## Groom 2026-09-25
- **Touches:**
  - `scripts/verify_red_ci.py` (rewrite, target about 300 lines)
  - `scripts/verify-red.sh` (thin)
  - `.github/workflows/ci.yml`: the verify-red job, plus `--cov` and diff-cover on the test (3.12) leg
  - `pyproject.toml`: the `control` marker, `diff-cover` in the dev extras
  - `tests/test_verify_red*.py`: rewritten, many old tests deleted with the machinery they pinned
  - `CONTRIBUTING.md`, `docs/testing.md`
  - `.claude/skills/pyrite-conductor/review.md`, `.claude/skills/pyrite-dev/`
- **Sequence:** early in 0.26; every other theme's evidence runs through it. It doesn't conflict with #381 or #387. It edits `ci.yml`, so don't run it beside another `ci.yml` theme (T1's test timeouts may touch `pytest` args: coordinate).
- **Model:** Opus (design-shaped). **Heavy:** no Playwright. **Cold read:** yes (CI, the process, and deleted tests).
- **Out of scope:** per-hunk revert (`test-evidence-per-hunk-revert-automates-the-guards-rule`, 0.27); making anything required in `gate`.
- Closes #368. Supersedes #374 and `verify-red-one-owner-for-revert-and-restore`.
