---
id: coordination-task-plugin
title: Coordination/Task Plugin
type: backlog_item
tags:
- feature
- extension
- plugin
kind: feature
effort: XL
---

## Problem

There is no structured way to track work items, assignments, or evidence chains within the knowledge graph. Tasks currently live outside Pyrite (GitHub issues, TODO comments) disconnected from the knowledge they produce.

## Proposed Solution

A `task` extension plugin with:

### Entry Type: `task`
- `status`: enum (open, in_progress, blocked, review, done)
- `assignee`: string (agent or human identifier)
- `dependencies`: array of entry IDs (tasks that must complete first)
- `evidence`: array of entry IDs (knowledge entries that support/fulfill this task)
- `priority`: int 1-10
- `due_date`: optional date

### MCP Tools (write tier)
- `task_claim` -- assign a task to the calling agent
- `task_complete` -- mark done with evidence links
- `task_flag` -- flag for human review with reason
- `task_list` -- query by status/assignee/priority

### Lifecycle Hooks
- `before_save`: validate status transitions (no skipping from open to done)
- `after_save`: auto-link evidence entries back to the task
- Blocked tasks auto-unblock when dependencies complete

### Key Insight

Tasks live in the same graph as the knowledge they produce. A task "Research actor X" links to the person entry it creates. This makes provenance traceable -- you can always ask "why does this entry exist?" and follow links back to the task that spawned it.

## Related

- pyrite/plugins/protocol.py -- PyritePlugin protocol
- extensions/ -- existing extension patterns (zettelkasten, cascade)

