---
id: kb-orchestrator-skill
title: "KB Orchestrator Skill for Multi-KB Agent Coordination"
type: backlog_item
tags:
- feature
- skill
- agents
- orchestration
kind: feature
priority: medium
effort: M
status: planned
links:
- bhag-self-configuring-knowledge-infrastructure
- launch-plan
- coordination-task-plugin
---

## Problem

Pyrite supports multiple KBs and the task plugin coordinates work within a KB. But there's no built-in pattern for cross-KB orchestration — an agent deciding which KBs are relevant, launching specialized agents with KB-specific context, routing findings between KBs, or monitoring progress across an investigation that spans multiple knowledge domains.

## Solution

A Claude Code / Claude Desktop skill (not a core feature) that provides the orchestration pattern. The orchestrator is the AI client, not Pyrite. Pyrite provides the tools; the skill provides the coordination logic.

### What the Skill Does

1. **Discovery**: Query all available KBs, their schemas, guidelines, and goals
2. **Planning**: Based on a high-level objective, determine which KBs are relevant and what work each needs
3. **Delegation**: Launch KB-specific agents (via task_decompose) with the right context loaded
4. **Routing**: When work in one KB produces results relevant to another (e.g., a confirmed finding that triggers a task), create cross-KB entries
5. **Monitoring**: Track task completion across KBs, surface blockers, report progress

### Skill Structure

```
.claude/skills/kb-orchestrator/
├── SKILL.md          # Orchestration methodology
├── discovery.md      # How to query KB landscape
├── planning.md       # How to decompose cross-KB work
├── delegation.md     # How to launch KB-specific agents
└── monitoring.md     # How to track cross-KB progress
```

### Key Patterns

- **KB capability assessment**: Read kb.yaml schemas to understand what each KB can do
- **Intent alignment**: Read KB-level goals to ensure work aligns with each KB's purpose
- **Cross-KB linking**: Use `[[kb:entry-id]]` shortlinks to connect related entries across KBs
- **Task fan-out**: Use task_decompose to create subtasks in different KBs
- **Rollup**: Monitor task completion across KBs, produce summary reports

## Prerequisites

- Task plugin phase 2 (atomic task_claim, task_decompose)
- Cross-KB shortlinks (done, #53)
- Intent layer phase 1 (KB-level goals — so orchestrator knows what each KB is trying to achieve)

## Success Criteria

- An agent using the skill can: discover KBs, assess their schemas, plan cross-KB work, delegate to specialized agents, and track completion
- Demo: "orchestrate a research project across a reference KB, investigation KB, and project KB"
- The skill works with Claude Code, Claude Desktop, and any MCP-capable client

## Launch Context

Post-0.8. Demonstrates the "agent swarm on shared infrastructure" story. Good for screencasts — watching an orchestrator coordinate work across KBs in real time.
