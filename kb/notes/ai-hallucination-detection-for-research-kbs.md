---
id: ai-hallucination-detection-for-research-kbs
title: AI hallucination detection for research KBs (Phase 3)
type: backlog_item
tags:
- qa
- fact-checking
- llm
- cascade
- agents
links:
- target: epic-migrate-kleptocracy-timeline-to-pyrite-managed-kb
  relation: subtask_of
  kb: pyrite
- target: source-url-validation-and-content-verification-for-qa
  relation: depends_on
  kb: pyrite
- target: source-content-verification-via-llm
  relation: depends_on
  kb: pyrite
kind: feature
status: proposed
priority: low
effort: L
---

## Problem

Research KBs populated by AI agents may contain fabricated claims that happen to cite real sources. Phase 1 checks URL liveness, Phase 2 checks source-claim alignment, but neither catches claims that have no source backing at all — the agent simply invented a fact.

## Context

This is Phase 3 of the source verification pipeline. Depends on both Phase 1 (URL checking) and Phase 2 (content verification). This is the most expensive phase as it requires web search API calls and LLM analysis.

## Scope

- For entries created by AI agents (check `provenance.created_by` or similar metadata)
- Web search for key claims to find independent corroboration
- Flag entries with no independent verification
- Prioritize high-importance entries (importance >= 8)
- Store results as QA assessment entries with evidence links

## Acceptance Criteria

- `pyrite qa check-hallucinations --kb=timeline --min-importance=8` checks high-priority entries
- Flags entries where web search finds no corroboration for key claims
- Stores results as QA assessment entries with evidence links
- Cost-controlled: respects `--max-cost` budget parameter
- Incremental: skips entries already checked unless `--force`

## Open Questions

- Which web search API? (Google, Bing, Brave, SerpAPI)
- How to extract "key claims" from an entry body for search queries?
- What confidence threshold for "no corroboration found" vs "insufficient search"?
- Should this also flag entries that contradict their own sources?
