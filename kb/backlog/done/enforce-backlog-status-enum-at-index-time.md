---
id: enforce-backlog-status-enum-at-index-time
title: "Enforce backlog status enum at index time + reconcile off-enum statuses"
type: backlog_item
tags: [software-kb, validation, data-health, index, backlog, status-enum]
importance: 5
kind: improvement
status: done
priority: medium
effort: S
rank: 0
---

## Problem

Backlog-item `status` drifted to off-enum values that nothing caught until a
manual grooming pass:

- **75 items** used `completed` — not in `BACKLOG_STATUSES` — which silently
  broke epic-progress rollups (the rollup counts `status == "done"`, so
  `completed` children read as not-done; `epic-normalization-and-data-cleanup`
  showed 0/10 when it was really 4/10). Cleaned up in commit `402f0a4`.
- **11 items** use `todo` and **4** use `superseded`, also absent from
  `BACKLOG_STATUSES`.

Root cause: the enum check (`_validate_enum(data, "status", BACKLOG_STATUSES,
...)` in `extensions/software-kb/src/pyrite_software_kb/validators.py`) only runs
under `pyrite kb validate` — NOT during `pyrite index sync` / `index health`,
where most drift is actually noticed. So invalid statuses accumulate silently and
corrupt downstream aggregates.

## Decision (status vocabulary)

- `superseded` is a legitimate terminal status (matches ADR vocabulary) →
  **add it to `BACKLOG_STATUSES`.**
- `todo` overlaps `planned` and is redundant in the active-state vocabulary →
  **rename the 11 `todo` items to `planned`** (no enum addition).
- `completed` was already normalized to `done`.

Canonical `BACKLOG_STATUSES` after this work:
`proposed, planned, accepted, in_progress, review, done, retired, deferred,
superseded, wont_do`.

## Solution

1. Add `superseded` to `BACKLOG_STATUSES` in
   `extensions/software-kb/src/pyrite_software_kb/entry_types.py`.
2. Rename the 11 `todo` backlog items to `planned`.
3. Surface invalid statuses as an **index-health warning** so drift is caught
   without running the full validator: add an `invalid_statuses` category to
   `IndexManager.check_health()` and render it in `pyrite index health`
   (alongside `undeclared_types`, `malformed_frontmatter`, etc.). This catches
   any future off-enum status the moment it's indexed.

## Acceptance criteria

- `superseded` accepted; no backlog item carries `todo` or `completed`.
- `pyrite index health` reports an `invalid_statuses` warning listing any
  backlog/ADR/milestone entry whose `status` is not in its declared enum.
- A unit test asserts the health check flags an off-enum status.
- Epic rollups remain correct (no regression from the status changes).

## Related

- Commit `402f0a4` — the grooming pass that surfaced and cleaned up the drift.
- `warn-on-undeclared-entry-type`, `schema-required-field-validation` (done) —
  the index-health-warning pattern this extends.
- `cli-error-shape-consistency` — adjacent consistency work.

## Resolution

Verified 2026-06-24: already fully implemented (work landed in the `402f0a4`
grooming pass and follow-ups, but the ticket was never closed).

- `superseded` is in `BACKLOG_STATUSES` (`entry_types.py:51`); canonical set
  matches the spec exactly.
- No backlog item carries `todo` or `completed`.
- `IndexManager.check_health()` populates `invalid_statuses` (`index.py:859`) and
  `pyrite index health` renders it (`index_commands.py:405-417`).
- Tests `TestInvalidStatusInHealth::{test_invalid_status_flagged,
  test_superseded_status_accepted}` (`tests/test_storage.py:1228+`) pass.

All acceptance criteria met — closing.
