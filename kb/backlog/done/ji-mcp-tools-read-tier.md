---
id: ji-mcp-tools-read-tier
title: 'Journalism-investigation: MCP tools (read tier)'
type: backlog_item
tags:
- journalism
- investigation
- plugin
- mcp
links:
- target: epic-core-journalism-investigation-plugin
  relation: subtask_of
  kb: pyrite
- target: ji-entity-entry-types
  relation: depends_on
  kb: pyrite
- target: ji-event-entry-types
  relation: depends_on
  kb: pyrite
- target: ji-connection-entry-types
  relation: depends_on
  kb: pyrite
kind: feature
status: done
assignee: claude
effort: M
---

## Problem

Agents working with journalism-investigation KBs need query tools for timelines, entity networks, source documents, claims, and money flows.

## Scope

6 read-tier MCP tools:

### `investigation_timeline`
- Query events by: date range, actor, tag, event type (event/transaction/legal_action), importance threshold
- Returns: events sorted by date, with actor and source counts
- Default limit: 50

### `investigation_entities`
- Query persons/orgs/assets/accounts by: type, importance, role, jurisdiction, tag
- Returns: entities sorted by importance
- Default limit: 50

### `investigation_network`
- Input: entity ID
- Returns: center entity + all connections (ownership, membership, funding) + direct event links + backlinks
- Depth: configurable (default 1 hop)

### `investigation_sources`
- Query source documents by: reliability, classification, date range, tag
- Returns: sources sorted by date

### `investigation_claims`
- Query claims by: status (unverified/corroborated/disputed/retracted), confidence, tag
- Returns: claims with linked evidence count

### `investigation_money_flow`
- Input: entity ID
- Returns: all transactions and funding relationships involving that entity, sorted by date
- Aggregates: total inflows, total outflows by counterparty

## Acceptance Criteria

- All 6 tools registered in MCP read tier
- Each tool returns structured JSON with consistent format
- Filters are optional (sensible defaults)
- Performance: <2s response for KBs up to 10,000 entries
