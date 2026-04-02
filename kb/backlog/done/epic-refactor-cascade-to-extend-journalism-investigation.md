---
id: epic-refactor-cascade-to-extend-journalism-investigation
title: 'Epic: Refactor Cascade to extend journalism-investigation base types'
type: backlog_item
tags:
- journalism
- investigation
- cascade
- refactoring
- epic
links:
- target: design-journalism-investigation-plugin
  relation: informed_by
  kb: pyrite
- target: epic-core-journalism-investigation-plugin
  relation: depends_on
  kb: pyrite
- target: ji-cascade-entry-type-inheritance
  relation: has_subtask
  kb: pyrite
- target: ji-cascade-mcp-tool-delegation
  relation: has_subtask
  kb: pyrite
- target: ji-cascade-migration-and-compat
  relation: has_subtask
  kb: pyrite
kind: epic
status: done
priority: medium
effort: L
---

## Overview

Refactor the Cascade plugin to inherit from journalism-investigation base types instead of duplicating them. Currently Cascade defines its own actor (extends PersonEntry), cascade_org (extends OrganizationEntry), and cascade_event/timeline_event (extends EventEntry). After this epic, Cascade extends the journalism-investigation versions of these types, gaining financial tracking, claims, and evidence chains for free.

## Inheritance Plan

```
journalism-investigation
├── person            → actor (adds: tier, era, capture_lanes, chapters)
├── organization      → cascade_org (adds: capture_lanes, chapters)
├── investigation_event → cascade_event (adds: era, capture_lanes, chapters)
├── investigation_event → timeline_event (adds: capture_lanes, actors, capture_type, connections, patterns)
├── investigation_event → solidarity_event (adds: infrastructure_types, lineage, legacy, capture_response, outcome)
└── (cascade-only) mechanism, scene, victim, statistic, theme
```

## Subtasks

1. **Entry type inheritance** — Cascade types extend journalism-investigation types instead of core types
2. **MCP tool delegation** — Cascade MCP tools delegate to journalism-investigation base where possible
3. **Migration and compatibility** — existing Cascade KBs continue to work, migration path for frontmatter changes

## Success Criteria

- Cascade plugin depends on journalism-investigation plugin
- All existing Cascade tests pass without modification
- Cascade KBs gain access to transaction, ownership, claim types via journalism-investigation
- No breaking changes to existing KB data
