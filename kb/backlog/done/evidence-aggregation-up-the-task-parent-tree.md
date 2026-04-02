---
id: evidence-aggregation-up-the-task-parent-tree
title: Evidence aggregation up the task parent tree
type: backlog_item
tags:
- task-system
- orchestration
links:
- target: epic-task-dag-queries-and-orchestrator-support
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
effort: S
---

When a child task accumulates evidence links, automatically aggregate them up to the parent task. This makes it possible to query a parent task and see all evidence from its subtree without manual collection.

## Impacted Files
- pyrite/services/task_service.py
- pyrite/models/task.py (possibly _parent_rollup hook)

## Acceptance Criteria
- Parent tasks show aggregated evidence from all children
- Aggregation happens automatically on child task update
- Evidence deduplication (same entry not listed twice)
