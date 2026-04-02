---
id: dependency-aware-auto-unblocking-for-tasks
title: Dependency-aware auto-unblocking for tasks
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

When a dependency task transitions to done, automatically check if any blocked tasks have all dependencies resolved and transition them from blocked to in_progress. Currently blocked tasks stay blocked until manually unblocked.

## Impacted Files
- pyrite/models/task_validators.py or core hooks
- pyrite/services/task_service.py

## Acceptance Criteria
- Blocked task auto-transitions to in_progress when all deps are done
- Only fires when the last blocking dependency completes
- Logged as an automatic transition (not manual)
