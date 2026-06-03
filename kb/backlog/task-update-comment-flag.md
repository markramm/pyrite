---
id: task-update-comment-flag
type: backlog_item
title: "Add `--comment` flag to `pyrite task update` for status-change audit trail"
kind: feature
status: proposed
priority: medium
effort: S
tags: [task-system, cli, audit-trail, conductor-workflow, grooming]
---

## Problem

`pyrite task update <id> -k <kb> --status done` walks the state machine but provides no slot for **why** the status changed. The audit trail of state transitions is currently fragmented across three surfaces:

1. The task's body field — agents append resolution notes manually, but the format isn't structured
2. Frontmatter mutation — git history shows the diff but no semantic reason
3. Commit messages — readable but disconnected from the task itself

The investigation-conductor's grooming workflow (`SKILL.md` Step 4) repeatedly walks tasks through state transitions with reasons that should be auditable:

- Stale-claim sweeps: walking 9 tasks from `in_progress` → `done` because deliverables exist + the worker is long-since-terminated
- Duplicate-merge close: walking a duplicate task to `done` with a pointer to the canonical task
- Watch-window passing: walking a `monitor-X-expected-2026-05-07` task to `done` because the trigger window passed without the expected event

The 2026-06-02 session ran a stale-claim audit (9 in_progress tasks walked to done with editorial-discipline justification documented in commit messages, not in the task records themselves). When the next conductor tick reads those tasks' status histories, the "why" is gone unless the agent reads the git log.

## Proposed solution

Add `--comment` flag to `pyrite task update`:

```
pyrite task update <id> -k <kb> --status done --comment "stale-sweep audit 2026-06-02: deliverables committed to KB; external-watch-only state; superseded by follow-up ticket <id>"
```

Comment is appended to a structured `status_change_log` (or similar) field in the task's frontmatter:

```yaml
status_change_log:
  - date: '2026-06-02T19:32:37Z'
    from: in_progress
    to: done
    by: investigation-conductor:stale-sweep-2026-06-02
    comment: "stale-sweep audit 2026-06-02: deliverables committed; external-watch-only; superseded by follow-up <id>"
```

Conductor synthesis can then query "show me all stale-sweep transitions in the last 7 days" or "show me all done transitions with comments mentioning FOIA" for grooming-pattern analysis.

## Related

- `add-blocked-on-optional-field-to-task-schema.md` (the blocker-taxonomy proposal addresses *why a task is held*; this proposal addresses *why a status transition happened*)
- `add-task-reset-command-for-stale-claims.md` (overlaps the stale-claim use case but addresses the reset mechanism specifically)

## Effort

S — schema field addition + CLI flag + minor index integration. No state-machine change.
