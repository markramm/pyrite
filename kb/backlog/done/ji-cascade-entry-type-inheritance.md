---
id: ji-cascade-entry-type-inheritance
title: Refactor Cascade entry types to extend journalism-investigation base
type: backlog_item
tags:
- journalism
- investigation
- cascade
- refactoring
links:
- target: epic-refactor-cascade-to-extend-journalism-investigation
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
effort: M
---

## Problem

Cascade defines `actor` (extends PersonEntry), `cascade_org` (extends OrganizationEntry), and multiple event types (extends EventEntry). After journalism-investigation plugin exists, these should extend the richer journalism-investigation types to inherit financial tracking, source management, and evidence chain capabilities.

## Scope

- Change `ActorEntry` to extend journalism-investigation's person type (or keep extending PersonEntry if journalism-investigation reuses core)
- Change `CascadeOrgEntry` to extend journalism-investigation's organization type
- Change `CascadeEventEntry`, `TimelineEventEntry`, `SolidarityEventEntry` to extend `InvestigationEventEntry`
- Add journalism-investigation as a dependency in Cascade's `pyproject.toml`
- Ensure all Cascade-specific fields are preserved
- Verify all 10 existing Cascade entry types still load/save correctly

## Acceptance Criteria

- All existing Cascade tests pass
- Cascade types inherit journalism-investigation fields (sources, verification_status, etc.)
- No frontmatter changes required in existing KB files (backward compatible)
- Plugin load order handles the dependency correctly
