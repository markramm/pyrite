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
status: proposed
priority: medium
effort: S
rank: 0
---

## Problem

`CHANGELOG.md` is the file every PR fights over: 11 of the window's commits touched it (2026-09-18, 04:00–06:30Z), and it was one of the two files that conflicted when `feature/smoke-e2e` rebased after `feature/playwright-foundation` merged. Every `[Unreleased]` bullet is appended at the same spot, so any two PRs in flight conflict there by construction. As the conductor keeps three workers in flight, every merge makes the others `BEHIND` and the CHANGELOG rebase is the manual step that stops auto-merge from being automatic.

## Fix

The towncrier pattern, hand-rolled or via towncrier: each PR adds `changelog.d/<slug>.<section>.md` (sections: security, added, changed, fixed, process, docs) — a new file never conflicts. `scripts/release.py` (roadmap 0.24.2) assembles the fragments into `CHANGELOG.md` under the version heading at release time and deletes them. A test in `tests/test_dev_process_config.py` asserts that `[Unreleased]` in `CHANGELOG.md` is empty on `dev` (bullets live in fragments) and that every fragment names a valid section. The `single-source-of-truth-for-the-version-asserted-by-a-test` item's `[Unreleased]` discipline moves onto this.

## Acceptance

- Two branches each adding a fragment rebase onto each other with no conflict (a test can simulate with `git` in a temp repo, or the PR shows it).
- `scripts/release.py --dry-run` prints the assembled section.
- Existing `[Unreleased]` bullets migrated to fragments in the same PR.
- pyrite-dev and pyrite-conductor skills say "add a fragment" where they say "add a CHANGELOG line".

Footprint: `CHANGELOG.md`, new `changelog.d/`, `scripts/release.py` (coordinate with the release-script theme if it is in flight — this may be the same PR), `tests/test_dev_process_config.py`, the two skills. Model: sonnet.
