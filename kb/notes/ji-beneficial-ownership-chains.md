---
id: ji-beneficial-ownership-chains
title: Beneficial ownership chain resolution
type: backlog_item
tags:
- journalism
- investigation
- financial
- ownership
links:
- target: epic-financial-relationship-tracking
  relation: subtask_of
  kb: pyrite
kind: feature
status: accepted
priority: high
effort: M
---

## Problem

Shell company structures obscure true ownership. An investigator needs to trace ownership chains: Person A owns Company B (80%), which owns Company C (51%), which owns Asset D — making Person A the beneficial owner of Asset D. This requires resolving ownership entry chains and computing effective ownership percentages.

## Scope

- Ownership chain traversal: follow `owns`/`owned_by` links through intermediaries
- Effective ownership calculation: multiply percentages along the chain
- Beneficial ownership flag: mark `beneficial: true` on ownership entries where the owner is a natural person
- Shell company detection: flag entities that own assets but have no employees, revenue, or physical presence
- CLI: `pyrite investigation ownership-chain <entity-id> --depth=5`
- MCP tool: `investigation_ownership_chain`

## Acceptance Criteria

- Ownership chains resolve through 5+ intermediary layers
- Effective ownership percentages calculated correctly (e.g., 80% × 51% = 40.8%)
- Beneficial owners (natural persons) identified at chain endpoints
- Shell company indicators flagged
