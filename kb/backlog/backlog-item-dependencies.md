---
id: backlog-item-dependencies
type: backlog_item
title: "Backlog item dependencies (blocked_by/blocks)"
kind: feature
status: done
priority: high
effort: M
tags: [software, agents, workflow, kanban]
links:
  - target: adr-0020
    relation: tracks
    note: "Dependency ordering for pull-based flow"
  - target: kanban-mcp-tools
    relation: tracks
    note: "sw_pull_next needs dependency awareness"
---

## Problem

`sw_pull_next` ranks by priority then age, but real backlogs have dependencies — "implement auth before user profiles." Without `blocked_by` relationships between backlog items, the system can recommend work that will fail because its prerequisite isn't done.

The link infrastructure already exists. The flow tools just don't use it for ordering.

## Solution

### New relationship type

Add `blocks`/`blocked_by` to the software-kb relationship types. Distinct from `tracks`/`tracked_by` (which means "this item is related to that ADR") — `blocks` means "this item must be done before that item can start."

### Flow tool changes

- **`sw_pull_next`**: Filter out items that have unresolved `blocked_by` links (where the blocking item's status is not `done`/`completed`). Include blocked items in a `blocked_items` field so the agent sees what's waiting.
- **`sw_context_for_item`**: Surface `blocks`/`blocked_by` in a dedicated `dependencies` bucket, showing status of each.
- **`sw_claim`**: Warn (or block, per policy) if claiming an item with unresolved dependencies.

### Backlog item frontmatter

Authors can express dependencies via standard links:

```yaml
links:
  - target: auth-system
    relation: blocked_by
    note: "Needs auth endpoints before user profiles"
```

### Prerequisite for decomposition

The work decomposition pattern (work-decomposition-pattern) needs parent/child tracking, which is a specialization of this dependency model. Build this first.
