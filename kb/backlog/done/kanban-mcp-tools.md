---
id: kanban-mcp-tools
title: "Add kanban flow tools: sw_pull_next, sw_context_for_item, sw_review_queue, sw_validate, sw_claim"
type: backlog_item
tags:
- mcp
- workflow
- agents
- software
- wave-2
- extension:software-kb
links:
- target: adr-0019
  relation: implements
  note: "MCP tool changes from the kanban ADR"
- target: adr-0020
  relation: implements
  note: "Review queue as computed view, not entity"
- target: software-project-plugin
  relation: part_of
- target: kanban-entity-types
  relation: depends_on
  note: "Needs milestone type and board config"
- target: standard-type-split
  relation: depends_on
  note: "sw_validate needs programmatic_validation type"
kind: feature
status: completed
priority: high
effort: L
---

# Add kanban flow tools

## Problem

Agents need flow-aware tools to pull work, get context, and submit for review. The key differentiator is context assembly — agents shouldn't have to figure out their own context.

## Solution

### CLI commands

- **`pyrite sw claim <item-id>`** — Claim a backlog item (atomic transition to in_progress, set assignee). Agents and humans use the same command.
- **`pyrite sw review-queue`** — Show items awaiting human review, sorted by wait time. Computed from backlog items in `review` status.
- **`pyrite sw submit <item-id>`** — Transition item from in_progress to review.

### MCP tools

- **`sw_pull_next`** (read tier) — Recommend what to work on given current WIP state. Reads board config for WIP limits, considers priority, dependencies. Returns item + context preview.
- **`sw_context_for_item`** (read tier) — Given a backlog item ID, assemble the full context bundle: relevant ADRs, component docs, programmatic validations, development conventions, and dependencies.
- **`sw_review_queue`** (read tier) — Surface items awaiting human review: what needs attention, wait time, what's blocking downstream work.
- **`sw_validate`** (write tier) — Run all relevant `programmatic_validation` entries against proposed changes. Returns pass/fail per validation.
- **`sw_claim`** (write tier) — Atomic claim of backlog item (same as CLI `sw claim`).

### REST API endpoints

- `GET /api/sw/review-queue` — Review queue with age/priority sorting
- `GET /api/sw/board` — Board state (items per lane, WIP usage)
- `POST /api/sw/claim/{item_id}` — Claim a backlog item
- `POST /api/sw/submit/{item_id}` — Submit for review

## Acceptance Criteria

- All five MCP tools registered (3 read, 2 write)
- `sw_pull_next` respects WIP limits and returns item + context preview
- `sw_context_for_item` assembles complete context bundle with links to all relevant entries
- `sw_validate` runs programmatic validation checks and returns structured pass/fail
- CLI commands work for both human and agent users
- REST API endpoints match CLI/MCP functionality
- Integration tests for each tool and command
