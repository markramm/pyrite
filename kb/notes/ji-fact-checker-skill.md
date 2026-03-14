---
id: ji-fact-checker-skill
title: Fact-checker agent skill for claim verification
type: backlog_item
tags:
- journalism
- investigation
- agents
- skills
- claims
links:
- target: epic-investigation-agent-workflows
  relation: subtask_of
  kb: pyrite
- target: ji-claim-lifecycle
  relation: depends_on
  kb: pyrite
kind: feature
status: accepted
effort: L
---

## Problem

Investigations accumulate unverified claims. A fact-checker agent skill can systematically evaluate claims, search for corroborating or contradicting evidence, and update claim status — maintaining the evidence chain throughout.

## Scope

- Claude Code skill for claim verification
- Input: claim ID or batch of unverified claims
- Process: read claim → search for corroborating sources → evaluate evidence → update claim status
- Creates: evidence entries linked to source documents
- Updates: claim status (unverified → partially_verified → corroborated/disputed)
- Updates: claim confidence based on evidence quality
- Flags: claims that cannot be verified (insufficient evidence)
- Cross-reference: checks if other claims in the KB contradict

## Acceptance Criteria

- Skill evaluates claims and produces evidence entries with source links
- Claim status updated through proper lifecycle transitions
- Evidence chains are complete: claim → evidence → source_document
- Cross-claim contradiction detection works
- Session logged with verification methodology and limitations
