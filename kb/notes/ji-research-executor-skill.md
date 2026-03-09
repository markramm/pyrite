---
id: ji-research-executor-skill
title: Research executor agent skill for investigations
type: backlog_item
tags:
- journalism
- investigation
- agents
- skills
links:
- target: epic-investigation-agent-workflows
  relation: subtask_of
  kb: pyrite
kind: feature
status: proposed
priority: medium
effort: L
---

## Problem

Creating investigation events and entity entries manually is slow. An agent skill that can systematically research a topic, create well-sourced events, and populate entity entries would accelerate investigation KB population.

## Scope

- Claude Code skill (`.claude/skills/`) for investigation research
- Input: research question or entity to investigate
- Process: web search → evaluate sources → create entries via MCP tools
- Creates: investigation_events, persons, organizations, document_sources
- Every created entry must have at least one source with reliability assessment
- Skill enforces source tier system (tier-1 preferred, tier-3 flagged)
- Deduplication: checks existing KB entries before creating new ones
- Outputs: summary of entries created, sources used, confidence assessment

## Acceptance Criteria

- Skill creates well-sourced investigation events from web research
- Every entry has source attribution with reliability rating
- Existing entities are linked, not duplicated
- Research session logged with decisions and open questions
