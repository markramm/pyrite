---
id: backlog-refinement-workflow
title: "Backlog refinement workflow using DoR gates"
type: backlog_item
tags:
- software-kb
- workflow
- agents
- grooming
links:
- target: adr-0021
  relation: implements
- target: definition-of-ready-done
  relation: related
kind: feature
status: done
assignee: claude
effort: L
---

## Problem

The DoR gate (ADR-0021) evaluates criteria at claim time, but ideally items should be refined *before* an agent tries to claim them. A grooming/refinement workflow would let a dedicated agent (or human) prepare backlog items so they pass the DoR gate before anyone claims them.

Currently there's no structured process for:
- Scanning the backlog for items that would fail DoR
- Systematically adding missing acceptance criteria, effort estimates, ADR links
- Moving items from `proposed` → `accepted` only when they're ready

## Scope

- Add an `sw_check_ready` MCP tool (or extend `sw_board`) that evaluates DoR criteria for items in `proposed`/`accepted` status without transitioning them
- Define a refinement workflow: scan backlog → identify DoR gaps → fill gaps → mark accepted
- Document the grooming agent pattern in the software-kb skill or a separate skill
- Consider a `pyrite sw refine` CLI command that lists items failing DoR with their gaps

## Design Considerations

- The `_evaluate_gate` method already exists and can be called without performing a transition
- A grooming agent should be able to run `sw_check_ready` on an item, see what's missing, update the item, and re-check
- This is complementary to the worker agent flow — worker agents check DoR at claim time, grooming agents check DoR proactively

## Acceptance Criteria

- Agent or human can check DoR status of any backlog item without claiming it
- Gaps are reported with actionable hints (already in gate criteria)
- Items that pass all DoR checkers can be confidently claimed by worker agents
