---
id: ji-claim-lifecycle
title: Claim entry type with lifecycle management
type: backlog_item
tags:
- journalism
- investigation
- claims
links:
- target: epic-evidence-and-claims-management
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
priority: high
assignee: claude
effort: M
---

## Problem

Investigative journalism produces specific factual assertions that need tracking through a verification lifecycle. "Entity X received $Y from Entity Z on Date D" is a claim that starts unverified, gains evidence, and eventually reaches corroborated or disputed status.

## Scope

### `claim` (ClaimEntry)
- Fields: `assertion` (text — the specific claim being made), `confidence` (high/medium/low), `status` (unverified, partially_verified, corroborated, disputed, retracted), `sources` (list of wikilinks to evidence/source entries), `disputed_by` (list of wikilinks to contradicting claims/evidence)
- Body: detailed narrative, context, significance

### Status Transitions
```
unverified → partially_verified → corroborated
                                → disputed → retracted
disputed → corroborated (if new evidence resolves dispute)
```

### Confidence Auto-Calculation
- 0 sources: low
- 1 source: low
- 2+ sources, same tier: medium
- 2+ sources, different tiers (cross-corroboration): high
- Disputed by credible source: drops to low regardless

### QA Integration
- Orphan claim warning: claim with no linked evidence
- Stale claim warning: unverified claim older than 30 days
- Confidence mismatch: manually set confidence disagrees with auto-calculation

## Acceptance Criteria

- Claim status transitions enforced (no skipping steps)
- Confidence auto-calculated from linked evidence count and source tiers
- QA validates orphan and stale claims
- Claims searchable by status, confidence, tag
- MCP tool `investigation_claims` queries claim state
