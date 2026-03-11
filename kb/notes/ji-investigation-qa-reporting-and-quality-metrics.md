---
id: ji-investigation-qa-reporting-and-quality-metrics
title: 'JI: Investigation QA reporting and quality metrics'
type: backlog_item
tags:
- ji
- qa
- metrics
kind: feature
effort: M
---

## Problem

An investigation needs aggregate quality metrics. Individual gap detection exists in the evidence chain tool, but there is no way to assess the overall health of an investigation: how many claims are unsupported, what percentage of sources are tier-1, how many stale unverified claims exist.

## Scope

### QA Metrics

- Source tier distribution: count and percentage of sources per reliability tier
- Claim coverage: percentage of claims with at least one evidence link
- Orphan claims: claims with zero evidence references
- Stale claims: unverified claims older than 30 days (configurable threshold)
- Confidence distribution: count of claims per confidence level
- Disputed claim ratio: percentage of claims in disputed/retracted status
- Investigation quality score: weighted composite of the above

### Integration Points

- MCP read-tier tool: `investigation_qa_report` returns structured metrics for a KB
- CLI command: `pyrite investigation qa -k KB` prints a formatted report
- Warnings surfaced in `investigation_claims` tool when orphan/stale claims are returned

### QA Rules (warnings, not blocking)

- Warning: investigation with less than 20% tier-1 sources
- Warning: claim marked corroborated but only has tier-3 sources
- Warning: more than 30% of claims are orphans (no evidence)
- Info: source reliability distribution breakdown

## Acceptance Criteria

- QA report returns all metrics listed above
- Configurable stale claim threshold (default 30 days)
- MCP tool and CLI command produce consistent output
- Quality score is a 0-100 number with documented formula
