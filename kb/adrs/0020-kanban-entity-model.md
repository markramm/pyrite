---
id: adr-0020
type: adr
title: "Kanban Entity Model: Lanes as Config, Review Queue as View"
adr_number: 20
status: accepted
date: 2026-03-08
deciders: [markr]
tags: [kanban, software-kb, architecture]
links:
  - target: adr-0019
    relation: refines
  - target: software-project-plugin
    relation: related
  - target: kanban-entity-types
    relation: related
  - target: kanban-mcp-tools
    relation: related
  - target: standard-type-split
    relation: related
---

# ADR-0020: Kanban Entity Model — Lanes as Config, Review Queue as View

## Context

ADR-0019 established pull-based kanban over sprint iterations for agent teams. It proposed three new entity types: `milestone`, `review_queue`, and `lane`. Implementation analysis revealed that these three concepts have fundamentally different natures that should drive different implementations.

The key question: which kanban concepts are **knowledge artifacts** (authored, searched, linked, versioned) and which are **operational infrastructure** (configuration, computed state)?

## Decision

### Milestone: entry type (knowledge artifact)

Milestones are real knowledge. People write them ("what does this release deliver?"), link backlog items to them, reference them in ADRs, track completion percentage. A milestone has a title, a body describing the goal, links to constituent items, and a status.

**Implementation:** New `milestone` entry type in software-kb extension with fields: `status` (open/closed), linked backlog items (via standard `links` frontmatter). Completion percentage computed from linked item statuses.

### Lane: board configuration (not an entry type)

Nobody authors a lane as a knowledge entry. Nobody searches for a lane, links to it, or reads its body. Lanes define workflow topology — they're board configuration that changes rarely. Creating individual markdown files for "Backlog", "In Progress", "Review", "Done" is make-work that produces no knowledge value.

**Implementation:** Board configuration in KB settings (YAML in kb config or a `board.yaml` file). Defines lane names, ordering, WIP limits, and transition policies. The kanban board (CLI and UI) reads this config to render columns and enforce limits.

Example board config:
```yaml
board:
  lanes:
    - name: Backlog
      statuses: [proposed, planned]
    - name: Ready
      statuses: [accepted]
    - name: In Progress
      statuses: [in_progress]
      wip_limit: 5
    - name: Review
      statuses: [review]
      wip_limit: 3
    - name: Done
      statuses: [done, completed]
  wip_policy: warn  # warn | enforce
```

Lanes map to existing backlog item statuses. No new status values needed — the board config groups statuses into visual lanes. This means the kanban view works immediately with existing backlog items.

### Review queue: computed view (not an entry type)

A review queue is a query result: "backlog items in review status, sorted by wait time, with WIP context." Nobody authors review queue entries. The queue is computed on demand from current backlog state.

**Implementation:** CLI command (`pyrite sw review-queue`), MCP tool (`sw_review_queue`), and API endpoint that query backlog items in review-mapped statuses. The board config's WIP limit for the review lane provides the capacity constraint.

### Standard type split: prerequisite

Per ADR-0019, `standard` splits into `programmatic_validation` (has a check command, pass/fail) and `development_convention` (judgment-based guidance). This must happen before `sw_validate` can work — the tool needs to know which entries define automated checks.

## Implementation Phases

### Phase 1: Standard type split
- New entry types: `programmatic_validation`, `development_convention`
- Migration of existing `standard` entries (3 enforced → validation, 32 not → convention)
- CLI: `pyrite sw validations`, `pyrite sw conventions`
- Deprecate `standard` type (keep as alias during transition)

### Phase 2: Milestone + board config
- New entry type: `milestone` with status and completion tracking
- Board config schema in KB settings
- CLI: `pyrite sw milestones`, `pyrite sw board`
- Backlog item: add `review` to BACKLOG_STATUSES for the review lane
- MCP: `sw_milestones` read tool

### Phase 3: Flow tools (agent-facing)
- `sw_pull_next` — recommend work given WIP state and agent capabilities
- `sw_context_for_item` — assemble full context bundle (ADRs, components, validations, conventions)
- `sw_review_queue` — computed view of items awaiting review
- `sw_validate` — run programmatic validations against changes
- `sw_claim` — atomic claim of backlog item (transition to in_progress)

### Phase 4: UI integration
- Kanban board view (lanes from config, cards from backlog items)
- Review queue panel
- Milestone progress bars
- Drag-and-drop status transitions

## Consequences

### Positive
- Lanes don't pollute the KB with content-free configuration entries
- Review queue stays always-current (computed, not manually maintained)
- Milestones serve their actual purpose as goal-oriented knowledge artifacts
- Board config is simple YAML that can be version-controlled alongside KB content
- Existing backlog items work immediately with the kanban view — no migration needed for lane support
- Standard split gives agents and the system clear automated-vs-judgment signals

### Negative
- Board config is a new concept (not an entry type) — needs documentation
- Lane customization requires editing YAML rather than creating entries
- Two-phase migration for standard type (deprecation period)

### Neutral
- The `lane` entity type from the original proposal could be added later if a use case emerges for lane-as-knowledge
- Board config could eventually move to the UI for visual editing
