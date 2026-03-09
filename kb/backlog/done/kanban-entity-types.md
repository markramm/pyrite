---
id: kanban-entity-types
type: backlog_item
title: "Milestone entry type, board config, and review workflow"
kind: feature
status: completed
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

# Milestone entry type, board config, and review workflow

## Problem

ADR-0019 established kanban flow for agent teams. ADR-0020 revised the entity model: milestone is a knowledge artifact (entry type), lanes are board configuration (YAML), review queue is a computed view (query). This item covers the entry type, extension config mechanism, and review workflow additions.

## Solution

### Extension config files

KBs already require specific extensions for their types (`kb_type: software` implies software-kb). Extensions can own config files in the KB root — separate from `kb.yaml` so each has its own git diff history and no namespace collisions.

For software-kb, the board config lives in `board.yaml` at the KB root:

```yaml
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

The extension reads this file from the KB path when needed. No changes to core `kb.yaml` schema required.

### Milestone entry type

New `milestone` entry type in software-kb extension:

- **Fields:** `status` (open/closed), standard `links` frontmatter for linked backlog items
- **Completion:** Computed from linked backlog item statuses (done/completed count vs total)
- **Validator:** Status enum, warns if no linked items
- **CLI:** `pyrite sw milestones` — lists milestones with completion percentage
- **MCP:** `sw_milestones` read tool

### Backlog item changes

- Add `review` to BACKLOG_STATUSES (new status for items awaiting human review)
- Workflow: add `in_progress → review` and `review → done`/`review → completed` transitions

### CLI

- `pyrite sw board` — show current board state (items per lane, WIP usage)
- `pyrite sw milestones` — list milestones with completion percentage

## Acceptance Criteria

- `milestone` type registered in software-kb plugin with validator
- Board config loaded from `board.yaml` in KB root
- `pyrite sw milestones` shows milestones with completion %
- `pyrite sw board` shows lane state with WIP usage
- `review` status added to backlog workflow
- Software preset template updated with default `board.yaml`
