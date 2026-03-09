---
id: epic-evidence-and-claims-management
title: 'Epic: Evidence and claims management'
type: backlog_item
tags:
- journalism
- investigation
- claims
- evidence
- epic
links:
- target: design-journalism-investigation-plugin
  relation: informed_by
  kb: pyrite
- target: epic-core-journalism-investigation-plugin
  relation: depends_on
  kb: pyrite
- target: ji-claim-lifecycle
  relation: has_subtask
  kb: pyrite
- target: ji-evidence-chain-tracking
  relation: has_subtask
  kb: pyrite
- target: ji-source-reliability-framework
  relation: has_subtask
  kb: pyrite
kind: epic
status: proposed
priority: high
effort: L
---

## Overview

The core differentiator of a journalism-investigation KB over raw data tools like Aleph: structured claim management with evidence chains and source reliability tracking. Every factual assertion links to source documents, each rated for reliability. Claims have a lifecycle from unverified to corroborated or disputed.

This is what makes an investigation publishable — the evidence chain from claim to source.

## Subtasks

1. **Claim lifecycle** — claim entry type with status transitions, corroboration tracking, dispute resolution
2. **Evidence chain tracking** — link claims to evidence to source documents, visualize chains
3. **Source reliability framework** — reliability ratings, source tier system, cross-source consistency checks

## Success Criteria

- Claims track from unverified → corroborated with linked evidence
- Evidence chains are traversable: claim → evidence → source_document
- Source reliability informs claim confidence automatically
- QA flags orphan claims (no evidence) and unsourced evidence
