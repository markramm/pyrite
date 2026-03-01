---
id: software-project-plugin
title: "Software Project Management Plugin (Wave 2)"
type: backlog_item
tags:
- feature
- plugin
- software
- agents
- wave-2
kind: feature
priority: high
effort: L
status: planned
links:
- launch-plan
- bhag-self-configuring-knowledge-infrastructure
- roadmap
---

## Problem

Dev teams using AI agents (Claude Code, Codex, OpenClaw) lack structured project knowledge. Architecture decisions live in scattered docs, component relationships are undocumented, and agents can't natively collaborate on a project's knowledge graph. Existing project management tools (GitHub Issues, Jira) track tasks but not knowledge — they don't capture the "why" behind architecture, the relationships between components, or the editorial standards that govern the codebase.

## Solution

Evolve the existing `extensions/software-kb/` into a full software project management plugin. The current extension already provides ADR, DesignDoc, Standard, Component, BacklogItem, and Runbook entry types with validators and CLI commands (`pyrite sw components`, `pyrite sw adrs`, `pyrite sw backlog`, `pyrite sw standards`, `pyrite sw new-adr`). The wave 2 work adds workflows, agent collaboration entity types, and task integration so agents can natively collaborate on a project.

### What Exists (software-kb extension)

- **Entry types**: ADR (7-status lifecycle), DesignDoc (5-status), Standard (category + enforced flag), Component (kind/path/owner/dependencies), BacklogItem (5-status workflow, priority, effort), Runbook (kind + audience)
- **Validators**: ADR number uniqueness, status enum enforcement, component dependency resolution
- **CLI**: `pyrite sw` subcommands for browsing and creating project artifacts
- **Workflows**: Basic status transitions on ADRs and backlog items
- **Preset**: `software` template for `pyrite init --template software`

### What's New for Wave 2

**Enhanced workflows:**
- BacklogItem workflow integration with the task plugin — backlog items become assignable tasks with agent claim/checkpoint semantics
- ADR approval workflow: draft → proposed → review → accepted with reviewer tracking
- Sprint/iteration planning: group backlog items into time-boxed iterations

**New entity types:**
- `sprint` — time-boxed iteration with goals, capacity, velocity tracking
- `dependency_map` — cross-component dependency visualization data
- `release` — release notes aggregated from completed backlog items and ADRs

**Agent collaboration:**
- Agents can claim backlog items as tasks (via task plugin integration)
- Agents can propose ADRs and submit for review
- Agents can update component documentation when they modify code
- Agents can generate release notes from completed items

**MCP tools (beyond existing CLI):**
- `sw_claim_item` — agent claims a backlog item (atomic, no double-claims)
- `sw_propose_adr` — create ADR in draft, auto-link to relevant components
- `sw_update_component` — update component docs with dependency changes
- `sw_sprint_status` — current sprint overview for agent context

### Relationship to Existing Extension

This is **not** a new plugin — it's the evolution of `extensions/software-kb/`. The existing entry types, validators, CLI commands, and preset remain. New features are additive. The `software` template continues to work. Backlog items should flow naturally into the backlog being tracked by this very project.

## Prerequisites

- Task plugin phase 2 (atomic task_claim, task_decompose) for agent collaboration
- Wave 1 platform shipped (0.8 alpha)

## Success Criteria

- Agent can claim a backlog item, implement it, update component docs, and mark it done — all via CLI or MCP
- ADR lifecycle works end-to-end: agent proposes → human reviews → accepted/rejected
- Sprint planning: create sprint, assign items, track velocity
- `pyrite init --template software` produces a working project KB with all new types
- Demo: "watch an agent collaborate on a software project" screencast

## Launch Context

This is the **wave 2** plugin. Launches 1-2 weeks after the 0.8 platform alpha. Audience: dev teams, Claude Code/Codex users. Message: "Agents that understand your architecture." The existing software-kb extension gives us a massive head start — most of the schema and infrastructure already exists.
