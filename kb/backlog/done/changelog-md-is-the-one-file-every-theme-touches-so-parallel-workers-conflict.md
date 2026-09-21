---
id: changelog-md-is-the-one-file-every-theme-touches-so-parallel-workers-conflict
title: CHANGELOG.md is the one file every theme touches, so parallel workers conflict there — and a conflicted PR gets ZERO checks, not just a rebase
type: backlog_item
tags:
- process
importance: 5
status: done
priority: medium
rank: 0
---

Second occurrence, and the first one that cost real time. Retro 1 already groomed the fix as a quality item (`changelog-fragments-one-file-per-pr-under-changelog-d-assembled-by-the-release`); this is the evidence that it should be dispatched rather than held as stock.

## What happened

PR #69 (CLI write-and-report correctness) went `CONFLICTING` / `mergeable_state: dirty` against `dev`. A `git merge-tree` against the merge base shows **exactly one conflicting file**:

```
changed in both
  base   CHANGELOG.md
  our    CHANGELOG.md
  their  CHANGELOG.md
```

Every other file in a 989-line, 14-file diff merges cleanly. Five PRs merged to `dev` while #69's worker was building, and each added its line to `[Unreleased]`.

## Why it cost more than a rebase

A conflicted PR is not just "rebase it". GitHub **stops computing the merge commit**, and with no merge commit it **runs no `pull_request` checks at all**:

```
$ gh api repos/markramm/pyrite/commits/<head>/check-runs --jq .total_count
0
```

The four other in-flight claim PRs (#81–#84) all show `checks=8` on their heads, so `synchronize` is working fine — #69 alone is starved, *because* it is conflicted. The worker noticed the missing checks and pushed an empty `ci: re-trigger PR checks on the pushed code` commit trying to shake them loose; it could not, because the cause was not a missed event. That is a worker spending commits on a diagnosis the conductor is better placed to make.

So the failure chain is: parallel workers → simultaneous `[Unreleased]` edits → conflict → no merge commit → **no checks at all** → a PR that looks unverified rather than conflicted, and a worker that misdiagnoses it.

## Why the fix is worth doing now

The loop is currently running five workers in parallel, and the cap may go to six. With one shared `CHANGELOG.md`, the probability that any two of them conflict approaches one as the cap rises — **the conflict rate scales with exactly the thing the loop is trying to increase**. It is the only file in the repo every theme touches by convention.

The groomed fix: one fragment file per PR under `changelog.d/`, assembled into `CHANGELOG.md` by the release script (`scripts/release.py`, itself an open 0.24.2 item — the two belong in the same theme). Fragments never conflict because no two PRs write the same path.

## Suggested acceptance

- A PR adds `changelog.d/<slug>.md` instead of editing `CHANGELOG.md`.
- The release assembles fragments into `[Unreleased]` in a deterministic order and deletes them.
- The `[Unreleased]`-discipline test (roadmap: "single source of truth for the version asserted by a test") asserts on the fragments, not the file.
- A test that two branches each adding a fragment merge without conflict.
- The pyrite-dev skill and `review.md`'s checklist stop saying "CHANGELOG `[Unreleased]` has a line per user-visible change" and say fragment instead.

Related: retro 1's quality stock item; `scripts/release.py` (0.24.2 DoD); the ADR-0032 row conflict retro 1 recorded on #39's rebase, which was the first occurrence.

Found in conductor tick 3, 2026-09-18, while absorbing #69.


## Triage 2026-09-20 (from GitHub)

**State: still open for a reason — leave open, and it is now unblocked.** (`process` issue; verified, not rewritten.)

Nothing has landed: there is no `changelog.d/` directory on `dev`, and `review.md`'s checklist still says "CHANGELOG `[Unreleased]` has a line per user-visible change". The mechanism this issue documents is intact — every theme edits one file, and a conflicted PR gets **zero** checks rather than a rebase prompt.

What has changed since filing is the sequencing note in the body: it says the fragment work "and `scripts/release.py` … belong in the same theme". `scripts/release.py` is now **PR #140**, open and in review, and it does not exist on `dev`. So the natural shape is: land #140, then a follow-up theme that (a) adds `changelog.d/`, (b) teaches the release script to assemble and delete fragments, (c) moves the `[Unreleased]`-discipline test onto the fragments, and (d) edits the two skills' checklist lines. The acceptance list in the body already covers all four and needs no rewriting.

One thing this issue's cost argument should now be read against: the machine budget caps the loop at **≤2 loop PRs ready at once** (#183, merged), so the conflict probability is lower than when this was filed at five-to-six parallel workers. That lowers the urgency; it does not change the mechanism, and outside contributors' PRs are not under the cap.


_Migrated from GitHub issue #103 on 2026-09-20 (maintainer: process findings live in the KB)._
