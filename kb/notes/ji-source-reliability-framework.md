---
id: ji-source-reliability-framework
title: Source reliability framework and tier system
type: backlog_item
tags:
- journalism
- investigation
- sources
- qa
links:
- target: epic-evidence-and-claims-management
  relation: subtask_of
  kb: pyrite
- target: ji-claim-lifecycle
  relation: depends_on
  kb: pyrite
kind: feature
status: done
assignee: claude
effort: S
---

## Problem

Not all sources are equal. A court filing is more reliable than an anonymous tip. Source reliability should inform claim confidence and investigation quality metrics.

## Scope

### Source Tier System

| Tier | Reliability | Examples |
|------|-------------|----------|
| 1 | High | Court filings, official records, financial disclosures, FOIA responses, corporate registries |
| 2 | Medium | Major news outlets, academic papers, public statements, congressional testimony |
| 3 | Low | Social media, anonymous tips, single-source reports, opinion pieces |

### Integration Points
- `document_source.reliability` field maps to tiers
- Claim confidence auto-calculation uses source tiers
- QA metrics: percentage of claims backed by tier-1 sources
- Investigation quality score: weighted average of source reliability across all claims

### QA Rules
- Warning: investigation with <20% tier-1 sources
- Warning: claim marked `corroborated` but only has tier-3 sources
- Info: source reliability distribution per investigation

## Acceptance Criteria

- Source tiers configurable per KB (override defaults in kb.yaml)
- Claim confidence calculation incorporates source tiers
- QA reports source tier distribution
- `investigation_sources` MCP tool filters by reliability
