---
id: review-outcome-capture
type: backlog_item
title: "Review outcome capture (sw_review tool)"
kind: feature
status: in_progress
priority: high
effort: M
tags: [software, agents, workflow, kanban, quality]
links:
  - target: adr-0020
    relation: tracks
    note: "Feedback loop for review workflow"
  - target: kanban-mcp-tools
    relation: tracks
    note: "Completes the review workflow with structured outcomes"
  - target: definition-of-ready-done
    relation: tracks
    note: "Review outcomes are the enforcement point for Definition of Done"
---

## Problem

The `review → done` and `review → in_progress` transitions exist in the workflow, but there's no tool to execute them with structured data. A reviewer (human or agent) has no way to record:

- Approved or changes requested
- What was good (reinforcement for future work)
- What needs rework (specific, actionable feedback)
- Whether Definition of Done criteria were met

Without this, review is just a status toggle. The system can't learn from review feedback, and agents repeating the same mistakes get no signal.

## Solution

### `sw_review` MCP tool (write tier)

- `item_id`, `kb_name` — the item under review
- `outcome` — `approved` or `changes_requested`
- `feedback` — structured review notes
- `reviewer` — who reviewed

If `approved`: transition `review → done` (or `completed`).
If `changes_requested`: transition `review → in_progress` with reason (required by workflow).

### CLI: `sw review <item-id> --outcome approved|changes_requested`

### Storage

Create a linked `review` entry (or append to work log) capturing the review outcome, feedback, and reviewer. This builds a history of reviews per item.

### Integration

- `sw_context_for_item` should surface prior review feedback so agents see what was rejected before and why
- Review queue (`sw_review_queue`) could show items on their second+ review cycle with a "rework count"
- Future: aggregate review patterns to identify recurring issues across the team
