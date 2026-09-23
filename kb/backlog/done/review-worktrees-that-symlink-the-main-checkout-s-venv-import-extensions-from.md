---
id: review-worktrees-that-symlink-the-main-checkout-s-venv-import-extensions-from
title: Review worktrees that symlink the main checkout's .venv import extensions/ from the main checkout, not the branch
type: backlog_item
tags:
- process
importance: 5
status: done
priority: medium
rank: 0
---

Conductor tick 2026-09-19 ~21:20Z, reviewing PR #187 (`fix/extension-base-field-conformance`).

The conductor's review worktrees were created with `git worktree add --detach` plus a symlink to `/Users/markr/pyrite/.venv` instead of `scripts/new-worktree.sh` (which builds a venv per worktree, and says why at lines 38-39). In the shared venv `pyrite` resolves to the worktree (pytest's rootdir puts it first on `sys.path`), but every extension package (`pyrite_social`, `pyrite_software_kb`, …) is an editable install pointing at `/Users/markr/pyrite/extensions/*/src` — the **main checkout on `dev`**, not the branch under review. Verified:

```
pyrite        -> /Users/markr/pyrite-wt/review-pr-187/pyrite/__init__.py
pyrite_social -> /Users/markr/pyrite/extensions/social/src/pyrite_social/__init__.py
```

The full suite on #187's head therefore reported `59 failed` — exactly the RED count of the branch's new conformance test — because the tests came from the branch and the extension code from `dev`. `scripts/verify-red.sh` then printed "fails without the fix (as it should)", which was vacuously true.

Blast radius: every other review this session (#184, #180, #161, #173, #145) changed only `pyrite/` and `tests/`, which resolve to the worktree, and verify-red on those genuinely flipped. Only branches that change `extensions/` are affected.

What should change:

1. `review.md`: say plainly that a review worktree is made with `scripts/new-worktree.sh review/<slug> origin/<branch>` *because of the editable-install rule*, and that a symlinked venv is wrong for any branch touching `extensions/`.
2. `scripts/verify-red.sh`: for each production file it reverts, resolve the file's top-level package and refuse (exit 2) when `<pkg>.__file__` is not under the worktree — a suite number from a tree the interpreter is not importing is not evidence.
3. Cheapest guard now: the conductor's checklist runs `python -c "import <pkg>; print(<pkg>.__file__)"` for `pyrite` and every extension package the diff touches before trusting a suite number.


## Triage 2026-09-20 (from GitHub)

**State: still open for a reason — leave open.** (`process` issue; verified, not rewritten.)

Checked against `dev` @130f433:

- **Change 1 (partly done).** `review.md:28` does say to use `scripts/new-worktree.sh review/<slug> origin/<branch>`, but it gives **#119's** reason (do not enter the worker's worktree), not this issue's: that a symlinked `.venv` resolves `extensions/*` to the **main checkout on `dev`** by editable install, so a suite run on a branch that changes `extensions/` measures a mixture of two trees. A reviewer who already has a review worktree by another route reads nothing that tells them their number is meaningless.
- **Change 2 (not done).** `scripts/verify-red.sh` has no package-resolution guard: no `__file__` check anywhere in it. The vacuous "fails without the fix (as it should)" this issue reports is still reachable.
- **Change 3 (not done).** No `python -c "import <pkg>; print(<pkg>.__file__)"` step in the checklist.

Change 2 is the one worth doing and it is small: for each production file `verify-red.sh` reverts, resolve the file's top-level package and **exit 2** when `<pkg>.__file__` is not under the worktree — the script already has an exit-2 "nothing was reverted, NO claim" path (`:47`) and this is the same claim, for the same reason. That turns the failure from a silently wrong green into a refusal.

Leaving open. Note it is the same family as #101 (a number measured in the wrong environment), one layer down, and #101's `review.md` rule does not reach it because the interpreter is the same one — only the *package* resolves elsewhere.


_Migrated from GitHub issue #189 on 2026-09-20 (maintainer: process findings live in the KB)._

## Done 2026-09-23 (retro 8)

Fixed by #206 (merged 2026-09-20); verified on dev at 6e505be. Left `proposed` for three days because nothing moves a KB item when the PR that fixes it merges.
