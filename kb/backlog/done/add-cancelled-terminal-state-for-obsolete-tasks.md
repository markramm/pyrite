---
id: add-cancelled-terminal-state-for-obsolete-tasks
title: "Add `cancelled`/`wontfix` terminal state for obsolete tasks (open → cancelled edge)"
type: backlog_item
tags: [task-system, conductor-workflow, workflow-state-machine, audit-honesty, grooming]
importance: 5
kind: feature
status: done
priority: medium
effort: S
rank: 0
---

## Problem

The task-workflow state machine (`TASK_WORKFLOW` in `pyrite/models/task.py`) has
two terminal states reachable only through work:

```
open → claimed → in_progress → {blocked, review, done, failed}
```

There is no terminal state for a task that is *obsolete* — redundant,
superseded, or no-longer-needed and never worked. Closing such a task forces
one of two dishonest options:

1. Walk it `open → claimed → in_progress → done` (three calls). This records it
   as **completed work that never happened** — it pollutes throughput/velocity
   signals and the work log with a phantom claim and a phantom in-progress span.
2. Mark it `failed`. This implies **someone tried and it broke**, which is also
   false.

Neither is semantically clean for "this task was redundant; nothing was done and
nothing should be." During grooming, an obsolete task is the common case, not an
edge case.

## How it surfaced

A conductor-side grooming pass tried to close a redundant, never-claimed task
with `pyrite task update <id> --status done` and hit the workflow guard
(`open → done` is not a legal edge). The error-rendering side of that was a
separate bug, now fixed (see "Related"). The *underlying* friction remains: even
done correctly, the only legal close path mislabels the task as completed work.

## Proposed solution

Add a `cancelled` terminal state (alias/naming TBD: `cancelled` vs `wontfix`) to
`TASK_WORKFLOW` with edges from every non-terminal state, since a task can be
recognized as obsolete at any point:

```
open        → cancelled
claimed     → cancelled
in_progress → cancelled
blocked     → cancelled
```

A `cancelled` task closes in **one call** and reads honestly: no work was
claimed or performed; the task was retired.

### Touch points

- `pyrite/models/task.py` — add the state to `TASK_WORKFLOW["states"]` and the
  transition edges; confirm any status enum / validation list includes it.
- `_task_validate_transition` (`pyrite/services/kb_service.py`) — no logic change
  needed beyond the new edges (it already drives off the workflow table).
- `_parent_rollup` (`pyrite/services/kb_service.py`) — decide whether a
  `cancelled` child counts toward parent auto-completion. Likely: a parent
  auto-completes when all children are in a terminal state (`done` **or**
  `cancelled`), so an all-cancelled parent doesn't hang open. Needs a deliberate
  choice.
- DAG / dependency logic (`pyrite/models/task.py` DAG helpers,
  `tests/test_task_dag.py`) — a `cancelled` task should unblock its dependents
  the same way `done` does (the blocker is resolved-by-removal), or be excluded
  from blocking entirely. Decide and test.
- Board / review views — surface `cancelled` distinctly from `done` so velocity
  and completion metrics don't conflate retired work with finished work.
- software-kb extension — its parallel `BACKLOG_WORKFLOW` already has
  `wont_do`/`rejected`/`deprecated` terminal states; align vocabulary or document
  why the task workflow and the backlog workflow differ.

## Why this matters

Honest terminal states are the difference between a task board you can trust for
throughput signals and one where "done" silently includes tasks nobody touched.
For an autonomously-groomed board (`/loop /investigation-conductor`), the
conductor closes obsolete tasks routinely; mislabeling them as `done` corrupts
exactly the signals the conductor reads back to pace itself.

## Acceptance criteria

- `cancelled` (or `wontfix`) terminal state added to `TASK_WORKFLOW` with edges
  from `open`, `claimed`, `in_progress`, and `blocked`.
- `pyrite task update <id> --status cancelled` closes a never-claimed task in one
  call.
- Parent-rollup behavior with cancelled children decided and tested.
- DAG dependent-unblocking behavior with a cancelled blocker decided and tested.
- Board/metrics views distinguish `cancelled` from `done`.
- Unit tests covering the new edges and the rollup/DAG decisions.

## Related

- `add-task-reset-command-for-stale-claims.md` — adjacent task-workflow gap
  (releasing stale `in_progress`/`blocked` claims back to `open`); both are about
  the lifecycle lacking clean off-ramps.
- `add-blocked-on-optional-field-to-task-schema.md` — adjacent task-schema work.
- Commit `0253402` — fixed the *error-rendering* half of this (illegal task
  transitions now show a helpful message instead of a traceback); this ticket is
  the *workflow-design* half.
