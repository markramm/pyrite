---
id: epic-core-journalism-investigation-plugin
title: 'Epic: Core journalism-investigation plugin'
type: backlog_item
tags:
- journalism
- investigation
- plugin
- epic
links:
- target: design-journalism-investigation-plugin
  relation: informed_by
  kb: pyrite
- target: ji-entity-entry-types
  relation: has_subtask
  kb: pyrite
- target: ji-event-entry-types
  relation: has_subtask
  kb: pyrite
- target: ji-connection-entry-types
  relation: has_subtask
  kb: pyrite
- target: ji-relationship-types-and-validators
  relation: has_subtask
  kb: pyrite
- target: ji-kb-preset-and-init-template
  relation: has_subtask
  kb: pyrite
- target: ji-mcp-tools-read-tier
  relation: has_subtask
  kb: pyrite
- target: ji-mcp-tools-write-tier
  relation: has_subtask
  kb: pyrite
kind: epic
status: accepted
priority: high
effort: XL
---

## Overview

Create the journalism-investigation Pyrite plugin — the foundational layer for investigative journalism KBs. Provides entry types for entities, events, connections, validators, a KB preset, and MCP tools. Informed by OCCRP's FollowTheMoney data model, adapted for Pyrite's markdown-first architecture.

## Subtasks

1. **Entity entry types** — person (reuse core), organization (reuse core), asset, account, document_source
2. **Event entry types** — investigation_event, transaction, legal_action
3. **Connection entry types** — ownership, membership, funding (edge-entities with their own properties)
4. **Relationship types and validators** — 10 relationship pairs, field validators per type
5. **KB preset and init template** — `pyrite init --template journalism-investigation`
6. **MCP tools (read tier)** — timeline, entities, network, sources, claims, money_flow queries
7. **MCP tools (write tier)** — create entity, event, claim, log source

## Success Criteria

- `pyrite init --template journalism-investigation` creates a fully configured KB
- All 15 entry types load, save, validate, and round-trip correctly
- MCP tools functional for entity/event/source CRUD and timeline/network queries
- Plugin discoverable via entry points, passes full test suite
- Design doc: [[design-journalism-investigation-plugin]]
