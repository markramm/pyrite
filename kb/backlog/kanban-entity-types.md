---
id: kanban-entity-types
type: backlog_item
title: "Add kanban entity types: milestone, review_queue, lane"
kind: feature
status: proposed
priority: high
effort: L
tags: [software, agents, workflow, wave-2]
links:
  - target: adr-0019
    relation: implements
    note: "Core entity types from the kanban ADR"
  - target: software-project-plugin
    relation: part_of
---

# Add kanban entity types: milestone, review_queue, lane

## Problem

ADR-0019 replaces the planned `sprint` entity type with three kanban-oriented types. These need to be implemented in the software-kb extension.

## Solution

Add three new entry types to `extensions/software-kb/`:

- **`milestone`** — Goal-oriented grouping. Fields: title, description, status (open/closed), items (linked backlog items). Milestones complete when all linked items complete.
- **`review_queue`** — Human review work surface. Fields: queue items with age/priority, WIP limit, current count. First-class representation of the human attention bottleneck.
- **`lane`** — Workflow stage. Fields: name, WIP limit, transition policies (entry/exit criteria), position in flow. Lanes define the kanban board topology.

Each type needs: entry class, validator, CLI browsing command (`pyrite sw milestones`, `pyrite sw review-queue`), and MCP read tools.

## Acceptance Criteria

- All three types registered in software-kb plugin
- Validators enforce WIP limits on lanes and review_queue
- `pyrite sw milestones` lists milestones with completion percentage
- `pyrite sw review-queue` shows items awaiting human review, sorted by age
- Software preset template updated to include lane definitions
