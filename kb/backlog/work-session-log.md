---
id: work-session-log
type: backlog_item
title: "Work session log for backlog items"
kind: feature
status: in_progress
priority: medium
effort: M
tags: [software, agents, workflow, kanban]
links:
  - target: adr-0020
    relation: tracks
    note: "Feedback and learning dimension for kanban flow"
  - target: kanban-mcp-tools
    relation: tracks
    note: "Extends flow tools with session context"
---

## Problem

The system is stateless between agent sessions. An agent claims an item, works, submits, and the only artifact is the code diff. There's no structured record of:

- What approach was tried and why
- What was attempted and rejected (and why it failed)
- Design tradeoffs made during implementation
- What's left open or uncertain

This knowledge evaporates. The next agent (or human reviewer) starts from scratch, repeats dead ends, or misunderstands design choices.

## Solution

A lightweight `sw_log` MCP tool (write tier) and CLI command that appends a structured work note to a backlog item. Called during or at the end of a work session.

### Fields

- `item_id` — the backlog item being worked
- `summary` — what was done this session
- `decisions` — design choices made and rationale (optional)
- `rejected` — approaches tried and abandoned, with reasons (optional)
- `open_questions` — unresolved issues for the next session (optional)

### Storage

Append as a linked `work_log` entry (or append to the item's body under a `## Work Log` section). Linked entries are cleaner — they preserve the original item body and allow multiple sessions.

### Integration

- `sw_context_for_item` should surface work log entries so the next agent sees prior session context
- `sw_submit` could prompt for a log entry before transition
- Review tool (future) can reference specific log entries in feedback
