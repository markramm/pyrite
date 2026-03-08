---
id: kanban-entity-types
type: backlog_item
title: "Add milestone entry type and board configuration"
kind: feature
status: proposed
priority: high
effort: L
tags: [software, agents, workflow, wave-2]
links:
  - target: adr-0019
    relation: implements
    note: "Core entity types from the kanban ADR"
  - target: adr-0020
    relation: implements
    note: "Revised entity model — milestone as entry, lanes as config"
  - target: software-project-plugin
    relation: part_of
  - target: standard-type-split
    relation: depends_on
    note: "Standard split should land first so sw_validate has types to work with"
---

# Add milestone entry type and board configuration

## Problem

ADR-0019 established kanban flow for agent teams. ADR-0020 revised the entity model: milestone is a knowledge artifact (entry type), lanes are board configuration (YAML), review queue is a computed view (query). This item covers the entry type and config work.

## Solution

### Milestone entry type

New `milestone` entry type in software-kb extension:

- **Fields:** `status` (open/closed), standard `links` frontmatter for linked backlog items
- **Completion:** Computed from linked backlog item statuses (done/completed count vs total)
- **Validator:** Status enum, warns if no linked items
- **CLI:** `pyrite sw milestones` — lists milestones with completion percentage
- **MCP:** `sw_milestones` read tool

### Board configuration

Board config in KB settings defines kanban topology:

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

Lanes map to existing backlog item statuses — no new status values needed except `review`.

### Backlog item changes

- Add `review` to BACKLOG_STATUSES (new status for items awaiting human review)
- Add `milestone` optional field for linking to a milestone
- Workflow: add `in_progress → review` transition

### CLI

- `pyrite sw board` — show current board state (items per lane, WIP usage)
- `pyrite sw milestones` — list milestones with completion percentage

## Acceptance Criteria

- `milestone` type registered in software-kb plugin with validator
- Board config schema defined and loaded from KB settings
- `pyrite sw milestones` shows milestones with completion %
- `pyrite sw board` shows lane state with WIP usage
- `review` status added to backlog workflow
- Software preset template updated with default board config
