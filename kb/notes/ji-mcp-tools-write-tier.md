---
id: ji-mcp-tools-write-tier
title: 'Journalism-investigation: MCP tools (write tier)'
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
- target: ji-mcp-tools-read-tier
  relation: depends_on
  kb: pyrite
kind: feature
status: proposed
priority: medium
effort: M
---

## Problem

Agents creating investigation content need write tools that enforce validation and maintain relationship integrity.

## Scope

4 write-tier MCP tools:

### `investigation_create_entity`
- Create person, organization, asset, or account entries
- Validates required fields per type
- Auto-generates ID from title
- Deduplication check: warns if entity with similar name/alias exists

### `investigation_create_event`
- Create investigation_event, transaction, or legal_action entries
- Validates date, required fields per subtype
- For transactions: validates sender/receiver exist (warns if not)
- For legal_actions: validates jurisdiction

### `investigation_create_claim`
- Create claim with evidence links
- Validates: at least one source or evidence link
- Sets initial status to `unverified`
- Warns if similar claim already exists (title similarity)

### `investigation_log_source`
- Log a source document with reliability assessment
- Fields: title, url, source_type, reliability, classification, obtained_method
- URL deduplication: warns if URL already logged
- Auto-checks URL liveness if check-urls capability is available

## Acceptance Criteria

- All 4 tools registered in MCP write tier
- Validation errors return clear messages, don't create partial entries
- Deduplication warnings are advisory, not blocking
- Created entries are immediately queryable via read-tier tools
