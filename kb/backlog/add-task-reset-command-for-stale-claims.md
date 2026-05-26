---
id: add-task-reset-command-for-stale-claims
type: backlog_item
title: "Add `pyrite task reset` command to release stale claims back to `open` status"
kind: feature
status: proposed
priority: medium
effort: S
tags: [task-system, conductor-workflow, claim-management, atomic-claim, stale-recovery]
---

## Problem

The conductor SKILL.md (`tcp-skills:investigation-conductor`) Step 4 — "Groom the Backlog" — explicitly directs the conductor to "Reset stale `in_progress` — tasks claimed in prior ticks but not completed within a reasonable window (24 hours for short tasks, longer for complex ones) may need claim-reset."

The Pyrite task-workflow state machine is forward-only:

- `open → in_progress` (via `task claim` or `task update -s in_progress`)
- `in_progress → done` (worker success)
- `in_progress → blocked` (worker hits external blocker)
- `blocked → done` (rare, but documented as the close path after blocker resolves)

Two transitions are forbidden by `_task_validate_transition`:
- `in_progress → open` (raises `ValueError: Invalid task transition`)
- `blocked → open` (same error)

This forward-only design is correct for normal workflow audit (workers shouldn't be able to silently un-claim work). But it leaves no clean path for the conductor to handle stale claims — i.e., tasks where a prior worker crashed, was killed, or completed without updating status, and the claim has aged past any reasonable working window.

## Current workaround (and why it's lossy)

The current workaround is `task update -s blocked` followed by `task update -a ""` to clear the assignee. Three problems:

1. **Semantic mismatch.** The task isn't blocked on an external resource (FOIA, interactive session, paywall) — it's blocked because the assignee died. Marking it `blocked` pollutes the blocked-task category, which the conductor uses as a signal for `blocked_pct > 30% → pause dispatch`. Stale-claim resets shouldn't count against that ceiling.
2. **Not re-dispatchable.** Once a task is `blocked`, the conductor's Step 5 dispatch logic filters for `status: open` and skips blocked tasks. To re-pursue the work, the user has to manually create a new task with a copy of the body — which loses the work log, the parent-epic linkage, and the original task identity.
3. **Documented as a memory-pinned bug.** This was hit on 2026-05-11 during a conductor tick that found a stale claim from 2026-05-08 (`research-blue-owl-cmbs-loan-servicer-425m-default-status`) and could not return it to `open` without lossy intervention. The same session reset four more stale claims from earlier ticks the same way.

## Proposed solution

Add `pyrite task reset` command:

```
pyrite task reset <task-id> -k <kb-name> [--reason "<short text>"]
```

Behavior:
1. Verify task is currently `in_progress` or `blocked` (refuse to reset `open` or `done`).
2. Verify the caller is the conductor / human operator, not an active worker holding the claim. Heuristic: refuse if the task's `updated_at` is within the last hour OR if there's a heartbeat / checkpoint within the last hour. For initial implementation, just require explicit `--force` flag if `updated_at < 1h ago`.
3. Set `status: open`, clear `assignee`, append a work-log entry: `Reset from {prior_status} by {operator} on {timestamp}. Reason: {reason or "stale-claim recovery"}.`
4. Bypass the normal state-machine validation (this is the privileged-recovery path).

Alternative naming: `pyrite task release` (matches Kubernetes / job-queue lock-release vocabulary).

## Why this matters

The conductor design contemplates parallel multi-agent worker dispatch with atomic claim safety. Atomic claim is the right primitive. But atomic claim only works if claim-release also works. Without a clean release primitive, every dropped worker creates permanent backlog cruft that requires the human operator to remember which tasks were dropped and to recreate them.

For a system designed to operate autonomously (`/loop /investigation-conductor`), claim-release is part of the basic operational hygiene, not an edge case.

## Acceptance criteria

- New `pyrite task reset` command in `pyrite/cli/task_commands.py`
- State-machine bypass implemented via a privileged-transition flag in `_task_validate_transition`
- Work log entry appended automatically (audit trail preserved)
- Optional `--force` flag for resets within the 1-hour-active window
- Conductor SKILL.md Step 4 updated to reference the new command instead of the current `update -s blocked` workaround
- Unit test for the reset path

## Related

- `/Users/markr/tcp-skills/plugins/tcp-skills/skills/investigation-conductor/SKILL.md` Step 4 grooming
- `add-blocked-on-optional-field-to-task-schema.md` — separate but adjacent task-system improvement
- Memory note in `/Users/markr/.claude/projects/-Users-markr-kb/memory/` flagging the stale-claim workflow trap discovered 2026-05-11
