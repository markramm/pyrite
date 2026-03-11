---
id: native-workflow-patterns-loops-checkpoints-parallel-batches
title: Native workflow patterns — loops, checkpoints, and parallel batches
type: backlog_item
tags:
- core
- agent-infrastructure
- workflows
- patterns
links:
- target: coordination-task-plugin
  relation: depends_on
  kb: pyrite
- target: epic-task-dag-queries-and-orchestrator-support
  relation: related_to
  kb: pyrite
- target: masfactory-integration-as-pyrite-orchestration-layer
  relation: related_to
  kb: pyrite
kind: feature
status: proposed
priority: medium
effort: M
---

## Problem

Pyrite's task system has the building blocks — decomposition, dependencies, checkpointing, parent rollup — but common multi-agent workflow patterns aren't formalized. Agents and skills re-invent these patterns in prose every time:

1. **Validate-fix loops** — "run QA, if issues > 0, fix and repeat, max 5 iterations." Every skill writes this as prose instructions. The task system has no loop primitive.
2. **Checkpoint-resume** — `task_checkpoint` exists but there's no standard for "resume from last checkpoint after interruption." Each skill handles this ad-hoc.
3. **Parallel batch scheduling** — `task_decompose` creates subtasks but there's no batch-aware scheduling that says "run these 5 in parallel, wait for all, then proceed." The parallel-agents skill doc describes the pattern but it's not encoded in the task system.

These patterns come from MASFactory's graph primitives (Loop, Gate, parallel node scheduling) but don't require a full execution engine — they can be formalized as task-system conventions and skill-level patterns.

## Scope

### 1. Loop pattern for tasks

A `loop` task type or convention where:
- Parent task has `max_iterations` and `termination_condition` fields
- Each iteration creates a checkpoint with iteration number and result summary
- Termination when: condition met, max iterations reached, or manual stop
- Concrete use case: QA validate-fix cycle

```yaml
---
id: qa-validate-fix-loop
type: task
title: "Validate and fix entry quality"
status: in_progress
loop:
  max_iterations: 5
  current_iteration: 2
  termination: "issues_count == 0"
agent_context:
  checkpoint: "Iteration 2: 3 issues remaining (down from 12)"
---
```

This is NOT an execution engine — it's metadata that skills and agents interpret. The task system tracks state; the agent (Claude) decides what to do each iteration.

### 2. Checkpoint-resume protocol

Formalize what a checkpoint contains so any agent can resume:
- **Last completed step** — which phase/iteration finished
- **Artifacts produced** — entry IDs created or modified
- **Pending work** — what remains to be done
- **Decision context** — why the agent made choices it made (from `sw_log`)

MCP tool enhancement: `task_resume` that reads the last checkpoint and returns a structured context bundle (similar to `sw_context_for_item` but for task resumption).

### 3. Parallel batch convention

A pattern for `task_decompose` where:
- Subtasks are tagged with a `batch` field (batch 1, batch 2, etc.)
- Within a batch, tasks run in parallel
- Between batches, tasks run sequentially (batch 2 waits for batch 1 to complete)
- Parent rollup is batch-aware: "batch 1 complete (5/5), batch 2 in progress (2/5)"

```yaml
# Parent task decomposes into:
- batch: 1  # These run in parallel
  tasks: [populate-concepts, populate-people, populate-events]
- batch: 2  # Waits for batch 1
  tasks: [validate-all, fix-orphans]
- batch: 3  # Waits for batch 2
  tasks: [web-research, final-validate]
```

### 4. Skill-level pattern documentation

Document these as reusable patterns that skills can reference:
- "Use the validate-fix loop pattern" → well-defined behavior
- "Use parallel batch scheduling" → well-defined behavior
- Skills become composable from named patterns rather than reinventing prose

## What This Is NOT

- **Not an execution engine** — no DAG scheduler, no automatic node dispatch
- **Not MASFactory inside Pyrite** — that's a separate integration item
- **Not new entry types** — extends the existing task system with conventions and optional fields
- **Not automatic** — agents still decide what to do; patterns provide structure and state tracking

## Acceptance Criteria

- Loop metadata fields supported on task entries (max_iterations, current_iteration, termination condition)
- `task_checkpoint` includes iteration tracking for loop tasks
- `task_resume` MCP tool returns structured context for resuming interrupted work
- Parallel batch convention documented and supported in `task_decompose`
- At least one skill (kb-lifecycle or QA) updated to use these patterns
- Existing task tests continue to pass
