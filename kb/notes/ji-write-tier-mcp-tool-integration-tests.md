---
id: ji-write-tier-mcp-tool-integration-tests
title: 'JI: Write-tier MCP tool integration tests'
type: backlog_item
tags:
- ji
- testing
- integration
kind: tech_debt
priority: high
effort: S
---

## Problem

The 4 write-tier MCP tools (investigation_create_entity, investigation_create_event, investigation_create_claim, investigation_log_source) are tested for schema and registration but have never been executed against a real DB. The handlers create entries via KBService but no integration test verifies the full round-trip: create via write tool, query back via read tool.

## Scope

Add integration tests that:

1. Set up a temporary KB with the journalism-investigation preset
2. Create entries via each write-tier tool handler
3. Query them back via the corresponding read-tier tool handler
4. Verify data integrity through the full round-trip

### Test Cases

- Create entity via write tool, find it via investigation_entities
- Create event via write tool, find it via investigation_timeline
- Create claim via write tool, find it via investigation_claims
- Log source via write tool, find it via investigation_sources
- Create claim with evidence refs, trace via investigation_evidence_chain
- Verify deduplication warnings (create same-title entity twice)
- Verify validation errors (create entity with invalid type)
- Verify claim created without evidence produces warning

## Acceptance Criteria

- All 4 write tools tested with real DB round-trip
- Error cases tested (invalid types, missing required fields)
- Warning cases tested (no evidence on claim, duplicate entity)
- Tests use tmp_path fixture, no persistent state
