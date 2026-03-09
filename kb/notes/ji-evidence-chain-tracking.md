---
id: ji-evidence-chain-tracking
title: Evidence chain tracking and visualization
type: backlog_item
tags:
- journalism
- investigation
- evidence
- graph
links:
- target: epic-evidence-and-claims-management
  relation: subtask_of
  kb: pyrite
- target: ji-claim-lifecycle
  relation: depends_on
  kb: pyrite
kind: feature
status: accepted
effort: M
---

## Problem

An investigation's credibility depends on traceable evidence chains: claim → evidence → source document. Investigators need to see which claims are well-sourced and which have gaps.

## Scope

### `evidence` (EvidenceEntry)
- Fields: `evidence_type` (document, testimony, record, data, photo, video, other), `source_document` (wikilink to document_source), `reliability` (high/medium/low), `obtained_date`, `chain_of_custody` (text — how this evidence was obtained and preserved)
- Links: `supports` claim (claim → sourced_from → evidence → sourced_from → document_source)

### Evidence Chain Queries
- `pyrite investigation evidence-chain <claim-id>` — show full chain from claim to source documents
- MCP tool: `investigation_evidence_chain` — returns structured chain graph
- Depth: claim → evidence entries → source documents → URLs

### Gap Detection
- Claims with no evidence links
- Evidence entries with no source document link
- Source documents with broken/unchecked URLs (integrates with URL validation)
- Cross-reference: do multiple independent evidence entries support the same claim?

## Acceptance Criteria

- Evidence chain traversable from claim to source document
- Gap detection identifies unsupported claims
- CLI and MCP tool produce structured chain output
- Graph view shows evidence network for an investigation
