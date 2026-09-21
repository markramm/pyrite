---
id: changelog-fragments-one-file-per-pr-under-changelog-d-assembled-by-the-release
title: 'CHANGELOG fragments: one file per PR under changelog.d/, assembled by the release script'
type: backlog_item
tags:
- quality
- process
- release
importance: 5
kind: tech_debt
status: done
priority: high
effort: S
rank: 0
---

## Problem

`CHANGELOG.md` is the file every PR fights over: 11 of the window's commits touched it (2026-09-18, 04:00–06:30Z), and it was one of the two files that conflicted when `feature/smoke-e2e` rebased after `feature/playwright-foundation` merged. Every `[Unreleased]` bullet is appended at the same spot, so any two PRs in flight conflict there by construction. As the conductor keeps three workers in flight, every merge makes the others `BEHIND` and the CHANGELOG rebase is the manual step that stops auto-merge from being automatic.

## Fix

The towncrier pattern, hand-rolled or via towncrier: each PR adds `changelog.d/<slug>.<section>.md` (sections: security, added, changed, fixed, process, docs) — a new file never conflicts. `scripts/release.py` (roadmap 0.24.2) assembles the fragments into `CHANGELOG.md` under the version heading at release time and deletes them. A test in `tests/test_dev_process_config.py` asserts that `[Unreleased]` in `CHANGELOG.md` is empty on `dev` (bullets live in fragments) and that every fragment names a valid section. The `single-source-of-truth-for-the-version-asserted-by-a-test` item's `[Unreleased]` discipline moves onto this.

## Evidence, 2026-09-20 (the release-prep window)

The cost is now measurable on outside contributors, not just on the loop's own
branches. In one session, **three** pull requests conflicted on `CHANGELOG.md`
and on nothing else:

- **#174** (makiaveli1) — `gh pr update-branch --rebase` failed outright with
  `RebaseConflictError`; the branch carried merge commits, so the rebase
  replayed its CHANGELOG entry into a spot `dev` had since filled. It took a
  merge-style update plus a squash to land.
- **#177** (Gambit-Checkmate) — blocked on it; the merged result was verified
  green (5210 passed) with the conflict resolved by keeping both entries.
- **#175** (makiaveli1) — same, 5215 passed once resolved.

In every case the two entries were pure adjacency: neither touched the other's
lines, and the resolution was "keep both, either order". No judgement was
involved, which is the definition of a conflict that should not exist.

The contributor-facing cost is the part that changed the priority: a
first-time contributor's PR now sits blocked on a merge conflict that has
nothing to do with their change, and the review has to explain that it is not
their fault.

## Acceptance

- Two branches each adding a fragment rebase onto each other with no conflict (a test can simulate with `git` in a temp repo, or the PR shows it).
- `scripts/release.py --dry-run` prints the assembled section.
- Existing `[Unreleased]` bullets migrated to fragments in the same PR.
- pyrite-dev and pyrite-conductor skills say "add a fragment" where they say "add a CHANGELOG line".

Footprint: `CHANGELOG.md`, new `changelog.d/`, `scripts/release.py` (coordinate with the release-script theme if it is in flight — this may be the same PR), `tests/test_dev_process_config.py`, the two skills. Model: sonnet.

## Groom 2026-09-18 (retro 5 — the oldest open `quality` theme; dispatch ahead of new features)

Evidence, 09:25Z–10:42Z: `CHANGELOG.md` was touched by 18 of the PRs merged
to `dev` since 05:00Z — the most of any file, ahead of the conductor skill
itself (12) — and at 10:42Z three of the six open loop branches (#145, #158,
#161) conflicted with `dev` on `CHANGELOG.md` and nothing else; #158 had been
flipped to ready with auto-merge armed and sat `DIRTY` for it.

Model: sonnet. Cold read: no. heavy: no. **Sequence: after #140 (`scripts/release.py`)
merges** — the assembly step lands in its `release_notes_for` / `compose_notes`,
which #140 owns until then; rebase onto it, do not run in parallel.

Acceptance (in addition to the item's own):
1. `changelog.d/<slug>.<section>.md`, sections `security added changed fixed process docs`;
   a test rejects an unknown section and an empty fragment.
2. `scripts/release.py` assembles fragments under the version heading in
   `compose_notes`, in section order, and deletes them under `--execute`; the
   dry run prints the assembled section. The existing `check_changelog` "still
   has entries" rule becomes "no fragments left and `[Unreleased]` empty".
3. Every existing `[Unreleased]` bullet migrated to a fragment in the same PR;
   `[Unreleased]` on `dev` holds only the `Target:` line afterwards, and
   `tests/test_dev_process_config.py` pins that.
4. A test builds two branches in a temp repo, each adding one fragment, and
   rebases one onto the other with no conflict.
5. pyrite-dev SKILL.md, pyrite-worker.md, dispatch.md and review.md say
   "add a fragment under `changelog.d/`" wherever they say "CHANGELOG line";
   CONTRIBUTING.md too.

Touches (existing): `CHANGELOG.md`, `scripts/release.py`, `tests/test_release_script.py`,
`tests/test_dev_process_config.py`, the four skill/agent files, `CONTRIBUTING.md`.
New: `changelog.d/` (+ a `README.md` in it naming the sections), the migrated
fragments, `tests/test_changelog_fragments.py`.

Regimes: an `[Unreleased]` that is already empty; a fragment whose section
is misspelled; two fragments with the same slug; a release with zero fragments
(the script must refuse, not publish an empty section).

Out of scope: towncrier as a dependency (hand-roll; it is ~60 lines); rewriting
released sections.
