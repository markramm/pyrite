---
id: definition-of-ready-done
title: "Support Definition of Ready and Definition of Done for backlog items"
type: backlog_item
tags:
- workflow
- agents
- quality
- software
- kanban
- extension:software-kb
links:
- target: adr-0020
  relation: tracks
  note: "Quality gates for the kanban workflow"
kind: feature
effort: L
status: done
---

## Problem

Software teams use "Definition of Ready" (DoR) and "Definition of Done" (DoD) as quality gates:

- **Definition of Ready**: Criteria a backlog item must meet before work can begin (e.g., acceptance criteria defined, linked to ADR if architectural, effort estimated, decomposed if XL+).
- **Definition of Done**: Criteria that must be satisfied before an item can move to `done`/`completed` (e.g., tests passing, validations run, documentation updated, PR merged).

## Design considerations

- DoR/DoD should be configurable per-KB (in board.yaml or a dedicated config file).
- Each criterion could be a checklist item (manual) or a reference to a programmatic validation (automated).
- `sw_claim` could check DoR and warn/block if not met.
- `sw_submit` or a review-approve tool could check DoD.
- Agents benefit from seeing DoR at claim time and DoD at submit time — reduces rework.
- Note: `sw_validate` as an MCP tool may be unnecessary — agents can run validation commands locally via pre-commit hooks and CI. The value is in surfacing _which_ validations apply to a given item (already handled by `sw_context_for_item`), not in executing them remotely.
