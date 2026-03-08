---
id: kanban-mcp-tools
type: backlog_item
title: "Add kanban MCP tools: sw_pull_next, sw_context_for_item, sw_review_queue, sw_validate"
kind: feature
status: proposed
priority: high
effort: L
tags: [software, agents, mcp, workflow, wave-2]
links:
  - target: adr-0019
    relation: implements
    note: "MCP tool changes from the kanban ADR"
  - target: software-project-plugin
    relation: part_of
  - target: kanban-entity-types
    relation: depends_on
    note: "Needs milestone, review_queue, lane types"
  - target: standard-type-split
    relation: depends_on
    note: "sw_validate needs programmatic_validation type"
---

# Add kanban MCP tools

## Problem

Agents need flow-aware tools that replace the planned `sw_sprint_status` with kanban primitives. The key differentiator is context assembly — agents shouldn't have to figure out their own context.

## Solution

Implement five MCP tools per ADR-0019:

- **`sw_pull_next`** — Recommend what to work on given agent capabilities and current WIP state. Considers lane WIP limits, priority, dependencies, and review queue depth.
- **`sw_context_for_item`** — Given a backlog item ID, assemble the full context bundle: relevant ADRs, component docs, programmatic validations, development conventions, and dependencies. This is the highest-value tool in the system.
- **`sw_review_queue`** — Surface items awaiting human review: what needs attention, wait time, what's blocking downstream work. Helps humans prioritize their review time.
- **`sw_validate`** — Run all relevant `programmatic_validation` entries against proposed changes. Returns pass/fail per validation. Automated gate before human review.
- **`sw_changelog_entry`** — Create structured changelog entries when agents complete work. Feeds the `release` entity type.

## Acceptance Criteria

- All five tools registered in write tier (sw_pull_next and sw_review_queue in read tier)
- `sw_pull_next` respects WIP limits and returns item + context preview
- `sw_context_for_item` assembles complete context bundle with links to all relevant entries
- `sw_validate` runs checks and returns structured pass/fail results
- Integration tests for each tool
