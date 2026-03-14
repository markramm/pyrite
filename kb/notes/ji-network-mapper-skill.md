---
id: ji-network-mapper-skill
title: Network mapper agent skill for relationship discovery
type: backlog_item
tags:
- journalism
- investigation
- agents
- skills
- graph
links:
- target: epic-investigation-agent-workflows
  relation: subtask_of
  kb: pyrite
- target: ji-connection-entry-types
  relation: depends_on
  kb: pyrite
kind: feature
status: accepted
effort: L
---

## Problem

Investigative journalism involves mapping networks of relationships — who owns what, who funds whom, who sits on which boards. Discovering and documenting these relationships is labor-intensive. An agent skill can systematically research and create connection entries.

## Scope

- Claude Code skill for relationship discovery
- Input: entity ID (person or organization) to map
- Process: research corporate registries, board memberships, funding disclosures → create connection entries
- Creates: ownership, membership, funding entries with source attribution
- Discovers: multi-hop connections (A owns B, B owns C)
- Sources: corporate registries, SEC filings, OpenCorporates, news reports
- Deduplication: checks existing connections before creating duplicates
- Output: network summary with new connections discovered

## Acceptance Criteria

- Skill discovers and documents ownership/membership/funding relationships
- Connection entries have source attribution and dates
- Multi-hop relationships flagged for further investigation
- Existing connections not duplicated
- Network summary shows entity connectivity score
