---
id: ji-cascade-mcp-tool-delegation
title: Cascade MCP tools delegate to journalism-investigation base
type: backlog_item
tags:
- journalism
- investigation
- cascade
- mcp
links:
- target: epic-refactor-cascade-to-extend-journalism-investigation
  relation: subtask_of
  kb: pyrite
- target: ji-cascade-entry-type-inheritance
  relation: depends_on
  kb: pyrite
kind: improvement
status: accepted
priority: low
effort: S
---

## Problem

Cascade's `cascade_timeline` and `cascade_actors` MCP tools duplicate query logic that journalism-investigation's `investigation_timeline` and `investigation_entities` tools will provide. After the type inheritance refactor, Cascade tools should delegate to the base implementations and add Cascade-specific filters (capture_lane, era, chapters).

## Scope

- `cascade_timeline` → wraps `investigation_timeline` + adds `capture_lane` filter
- `cascade_actors` → wraps `investigation_entities` + adds `era`, `tier` filters
- `cascade_network` → wraps `investigation_network` (no changes needed)
- Cascade-only tools (`solidarity_timeline`, `cascade_capture_lanes`, `solidarity_infrastructure_types`) stay as-is

## Acceptance Criteria

- Cascade MCP tools return identical results to current behavior
- Reduced code duplication between plugins
- New journalism-investigation query capabilities (money_flow, claims) available in Cascade KBs
