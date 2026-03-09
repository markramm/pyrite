---
id: task-critical-path-analysis-via-dependency-graph-traversal
title: Task critical path analysis via dependency graph traversal
type: backlog_item
tags:
- task-system
- orchestration
kind: feature
effort: M
links:
- target: epic-task-dag-queries-and-orchestrator-support
  relation: subtask_of
  kb: pyrite
---

Add task_critical_path query that finds the blocking chain for a given task by traversing the dependency graph. Returns the longest path of unresolved dependencies. Useful for orchestrators to identify what to unblock first.

## Impacted Files
- pyrite/services/task_service.py
- pyrite/server/mcp_server.py (new MCP tool)

## Acceptance Criteria
- task_critical_path returns ordered list of blocking tasks
- Handles cycles gracefully (detects and reports)
- Available as both MCP tool and CLI command

