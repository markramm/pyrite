---
id: epic-financial-relationship-tracking
title: 'Epic: Financial relationship tracking and money flow analysis'
type: backlog_item
tags:
- journalism
- investigation
- financial
- epic
links:
- target: design-journalism-investigation-plugin
  relation: informed_by
  kb: pyrite
- target: epic-core-journalism-investigation-plugin
  relation: depends_on
  kb: pyrite
- target: ji-money-flow-queries
  relation: has_subtask
  kb: pyrite
- target: ji-beneficial-ownership-chains
  relation: has_subtask
  kb: pyrite
- target: ji-ftm-import-export
  relation: has_subtask
  kb: pyrite
kind: epic
status: done
priority: medium
effort: L
---

## Overview

Build the "follow the money" analysis layer on top of the core journalism-investigation plugin. This epic adds money flow tracing across transaction chains, beneficial ownership resolution through shell company layers, and interoperability with OCCRP's FollowTheMoney data format.

## Subtasks

1. **Money flow queries** — trace transaction chains, aggregate flows by entity/time, detect circular flows
2. **Beneficial ownership chains** — resolve ownership through intermediaries, flag shell company patterns
3. **FtM import/export** — import/export entities in FollowTheMoney JSON format for Aleph interop

## Success Criteria

- `investigation_money_flow` traces multi-hop transaction chains
- Beneficial ownership resolves through shell companies to natural persons
- FtM import loads OCCRP data into a journalism-investigation KB
- FtM export produces valid FollowTheMoney JSON for Aleph upload
