---
id: ji-money-flow-queries
title: Money flow query and visualization support
type: backlog_item
tags:
- journalism
- investigation
- financial
- graph
links:
- target: epic-financial-relationship-tracking
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
priority: high
effort: M
---

## Problem

Following the money requires tracing transaction chains across multiple hops. A payment from A→B and B→C should be discoverable as a flow from A→C. Investigators need to aggregate flows by entity and time period, and detect circular patterns (A→B→C→A).

## Scope

- Multi-hop transaction chain traversal via graph queries
- Aggregate inflows/outflows per entity with time bucketing
- Circular flow detection (money laundering pattern)
- CLI command: `pyrite investigation money-flow <entity-id> --hops=3 --from=2020 --to=2025`
- MCP tool enhancement: `investigation_money_flow` with depth parameter
- Output: structured flow graph with amounts, dates, and intermediaries

## Acceptance Criteria

- 3-hop transaction chains discoverable from any entity
- Aggregate view: total in/out per counterparty per year
- Circular flows flagged with confidence indicator
- Performance: <5s for chains up to 1,000 transactions
