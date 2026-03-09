---
id: ji-claim-to-edge-promotion
title: Claim-to-edge promotion workflow for corroborated relationships
type: backlog_item
tags:
- journalism
- investigation
- claims
- graph
- workflow
links:
- target: epic-evidence-and-claims-management
  relation: subtask_of
  kb: pyrite
- target: ji-claim-lifecycle
  relation: depends_on
  kb: pyrite
- target: ji-connection-entry-types
  relation: depends_on
  kb: pyrite
kind: feature
status: proposed
priority: medium
effort: S
---

## Problem

The claim/edge-entity separation (ADR-0022) creates a workflow gap. An agent researching an investigation will:

1. Find evidence suggesting "Person A owns Company B" — creates a claim (unverified)
2. Find corroborating sources — updates claim to corroborated
3. Now needs to create an ownership edge-entity to make this relationship structural

Step 3 is easy to forget. The corroborated claim sits in the KB but the graph doesn't reflect it. The agent has to manually extract entities from the claim and create the edge-entity, duplicating information.

## Scope

- MCP tool: `investigation_promote_claim` — converts a corroborated claim about a relationship into an edge-entity
- Reads the claim, identifies the entities and relationship type
- Creates the edge-entity with endpoints extracted from the claim
- Links the edge-entity back to the claim as provenance (`sourced_from` relation)
- Only works on claims with status `corroborated` or `partially_verified`
- Dry-run mode: show what would be created without creating
- CLI equivalent: `pyrite investigation promote-claim <claim-id> --edge-type=ownership`

## Example Flow

```
Agent finds evidence: "Putin owns 51% of Company X via Cyprus nominee"
  → creates claim (unverified)
  → finds Panama Papers doc confirming it
  → updates claim to corroborated

Agent (or automated rule): promote corroborated claim to edge
  → investigation_promote_claim(claim_id, edge_type="ownership")
  → creates ownership entry: owner=putin, asset=company-x, percentage=51
  → links ownership entry → sourced_from → claim → sourced_from → evidence → panama-papers-doc
```

## Acceptance Criteria

- Promotion creates edge-entity with correct endpoints extracted from claim
- Edge-entity links back to originating claim as provenance
- Only corroborated or partially_verified claims can be promoted
- Dry-run shows proposed edge-entity without creating
- Duplicate detection: warns if similar edge-entity already exists
