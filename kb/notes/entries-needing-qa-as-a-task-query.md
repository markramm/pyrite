---
id: entries-needing-qa-as-a-task-query
title: Entries needing QA as a task query
type: backlog_item
tags:
- task-system
- qa
links:
- target: epic-task-system-integration-with-qa-agent
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
effort: S
---

Add a query mode to task_list that returns all entries that need QA review, based on open/unclaimed QA validation tasks. This gives QA agents a single command to find their work queue.

## Impacted Files
- pyrite/services/task_service.py
- pyrite/server/mcp_server.py
- pyrite/cli/task_commands.py

## Acceptance Criteria
- task_list --qa-queue returns entries with open QA tasks
- Sorted by priority and age
- Available via MCP and CLI
