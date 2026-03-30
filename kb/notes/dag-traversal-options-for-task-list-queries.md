---
id: dag-traversal-options-for-task-list-queries
title: DAG traversal options for task_list queries
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
effort: M
---

Extend task_list MCP tool and CLI command with DAG traversal modes: subtree (all descendants), ancestors (all parents), and blocked-by (transitive dependency chain). Currently task_list only does flat filtering.

## Impacted Files
- pyrite/services/task_service.py
- pyrite/server/mcp_server.py (extend task_list tool schema)
- pyrite/cli/task_commands.py

## Acceptance Criteria
- task_list --subtree <id> returns all descendants
- task_list --ancestors <id> returns parent chain
- task_list --blocked-by <id> returns transitive blockers
- Works via both MCP and CLI
