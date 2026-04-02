---
id: epic-investigation-agent-workflows
title: 'Epic: Investigation agent workflows and skills'
type: backlog_item
tags:
- journalism
- investigation
- agents
- skills
- epic
links:
- target: design-journalism-investigation-plugin
  relation: informed_by
  kb: pyrite
- target: epic-core-journalism-investigation-plugin
  relation: depends_on
  kb: pyrite
- target: epic-evidence-and-claims-management
  relation: depends_on
  kb: pyrite
- target: ji-research-executor-skill
  relation: has_subtask
  kb: pyrite
- target: ji-fact-checker-skill
  relation: has_subtask
  kb: pyrite
- target: ji-network-mapper-skill
  relation: has_subtask
  kb: pyrite
kind: epic
status: done
priority: medium
effort: XL
---

## Overview

Agent skills purpose-built for investigative journalism workflows. These enable AI agents to systematically research entities, verify claims, and map relationship networks using the journalism-investigation plugin's entry types and MCP tools.

## Subtasks

1. **Research executor skill** — agent skill for systematic entity research and event creation
2. **Fact-checker skill** — agent skill for claim verification and evidence chain building
3. **Network mapper skill** — agent skill for discovering and documenting entity relationships

## Success Criteria

- Research executor can create well-sourced investigation events from web research
- Fact-checker can evaluate claims, find corroborating/contradicting evidence, update claim status
- Network mapper can discover ownership/membership/funding relationships and create connection entries
- All skills produce entries with proper source attribution and evidence chains
