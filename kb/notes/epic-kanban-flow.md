---
id: epic-kanban-flow
title: "Epic: Complete kanban flow for agent dev sessions"
type: backlog_item
tags:
- workflow
- agents
- software
- epic
- kanban
- extension:software-kb
links:
- target: adr-0019
  relation: implements
- target: adr-0020
  relation: implements
- target: kanban-entity-types
  relation: tracks
  note: "Completed — milestone type, board config, review workflow"
- target: kanban-mcp-tools
  relation: tracks
  note: "Completed — sw_pull_next, sw_context_for_item, sw_review_queue, sw_claim"
- target: backlog-item-dependencies
  relation: tracks
  note: "Pending — blocked_by/blocks for sw_pull_next ordering"
- target: review-outcome-capture
  relation: tracks
  note: "Pending — sw_review tool to close the feedback loop"
- target: work-session-log
  relation: tracks
  note: "Pending — structured session context for handoffs"
- target: work-decomposition-pattern
  relation: tracks
  note: "Pending — XL+ decomposition before claim"
- target: definition-of-ready-done
  relation: tracks
  note: "Pending — quality gates at claim and submit"
kind: epic
status: in_progress
priority: high
effort: XL
---

## Goal

A complete pull-based kanban workflow where agents can autonomously pick up work, get full context, execute, submit for review, and receive structured feedback — with guardrails (WIP limits, dependency ordering, decomposition rules, quality gates) that prevent common failure modes.

## Completed

- Milestone entry type and board config (lanes, WIP limits, wip_policy)
- Review workflow transitions (in_progress → review → done/completed)
- Flow tools: sw_pull_next, sw_context_for_item, sw_review_queue, sw_claim
- CLI: sw claim, sw submit, sw review-queue
- Backlog item dependencies (blocked_by/blocks) — sw_pull_next skips blocked, sw_claim refuses blocked
- Review outcome capture (sw_review) — approve/changes_requested with feedback, review records
- Work session log (sw_log) — structured session notes linked to items via session_for/has_session

## Remaining

- Work decomposition — XL+ items must decompose before claim
- Definition of Ready/Done — quality gates for status transitions
