---
id: research-workflow-templates-for-journalist-use-cases
title: Research Workflow Templates for Journalist Use Cases
type: backlog_item
tags:
- journalism
- agents
- orchestration
- workflow
links:
- target: epic-journalists-pyrite-wiki-hosted-research-platform-for-independent-journalists
  relation: subtask_of
  kb: pyrite
importance: 5
---

## Problem

Running a multi-agent research workflow requires composing agent configs, tool selections, and output schemas from scratch. Journalists need repeatable patterns they can launch with a goal and minimal configuration.

## Solution

Pre-built workflow templates that define agent roles, tool access, and output schemas:

1. **Seed and Extend** -- Start from a pre-populated KB, fan out agents to find connections and extend with new findings. Primary journalist use case.
2. **Deep Research** -- Fan out N research agents across KB + external sources, synthesize into a structured findings document.
3. **KB Audit** -- Scan for gaps, stale entries, broken source chains, missing cross-links. Produce improvement proposals as backlog items.
4. **Cross-KB Investigation** -- The kb-orchestrator-skill pattern: discover relevant KBs, decompose work across them, route findings between KBs.
5. **Entity Network Mapping** -- Given a person or organization, trace connections across KBs, produce a relationship map.

### Template Format

Templates are KB entries (type: workflow_template) with:
- Agent role definitions (names, system prompts, tool access)
- Output schema (Zod-like spec for structured results)
- Default parameters (which KBs to search, output types)
- User-configurable parameters (goal, scope constraints, max tokens)

## Success Criteria

- At least 3 templates available at launch
- Templates are editable by admin users
- A journalist can select a template, enter a goal, and launch
