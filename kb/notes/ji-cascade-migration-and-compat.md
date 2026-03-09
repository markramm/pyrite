---
id: ji-cascade-migration-and-compat
title: Cascade migration path and backward compatibility
type: backlog_item
tags:
- journalism
- investigation
- cascade
- migration
links:
- target: epic-refactor-cascade-to-extend-journalism-investigation
  relation: subtask_of
  kb: pyrite
- target: ji-cascade-entry-type-inheritance
  relation: depends_on
  kb: pyrite
kind: feature
status: proposed
priority: medium
effort: S
---

## Problem

Existing Cascade KBs (cascade-research, cascade-timeline, cascade-solidarity) must continue working after the refactor. Frontmatter in existing markdown files must be forward-compatible. If journalism-investigation adds new required fields, existing entries must not fail validation.

## Scope

- Audit all journalism-investigation field additions for backward compatibility
- New fields must have sensible defaults (e.g., `verification_status` defaults to `unverified`)
- Schema migration: if any field names change, add migration in Cascade's migration.py
- Test: load all 3 existing Cascade KB types, verify zero validation errors
- Document migration path for users upgrading Cascade

## Acceptance Criteria

- Existing Cascade KBs load without errors after refactor
- No manual frontmatter changes required
- Schema migration handles any field renames automatically
- `pyrite qa validate` passes on existing Cascade data
