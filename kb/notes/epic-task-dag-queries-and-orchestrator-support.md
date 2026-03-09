---
id: epic-task-dag-queries-and-orchestrator-support
title: 'Epic: Task DAG queries and orchestrator support'
type: backlog_item
tags:
- task-system
- orchestration
- epic
kind: epic
effort: L
links:
- target: task-critical-path-analysis-via-dependency-graph-traversal
  relation: has_subtask
  kb: pyrite
- target: evidence-aggregation-up-the-task-parent-tree
  relation: has_subtask
  kb: pyrite
- target: dag-traversal-options-for-task-list-queries
  relation: has_subtask
  kb: pyrite
- target: dependency-aware-auto-unblocking-for-tasks
  relation: has_subtask
  kb: pyrite
---

Phase 3 of the Coordination/Task System. Adds DAG traversal, critical path analysis, evidence aggregation, and dependency-aware unblocking to the task system. Builds on the core task infrastructure (Phases 1-2, now complete).

## Acceptance Criteria

- Critical path analysis identifies blocking chains
- Evidence links aggregate up the parent tree
- task_list supports DAG traversal (subtree, ancestors, blocked-by)
- Blocked tasks auto-transition to in_progress when dependencies complete

