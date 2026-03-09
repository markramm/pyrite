---
id: source-url-validation-and-content-verification-for-qa
title: Source URL validation and content verification for QA
type: backlog_item
tags:
- qa
- sources
- fact-checking
- validation
- cascade
links:
- target: epic-migrate-kleptocracy-timeline-to-pyrite-managed-kb
  relation: subtask_of
  kb: pyrite
kind: feature
status: accepted
effort: L
---

## Problem

Pyrite's QA service validates structural aspects of entries (required fields, date formats, schema compliance) but does not verify that source URLs are valid or that entry content is consistent with cited sources. This is a significant gap for research KBs where entries are created by AI agents that may hallucinate details or cite non-existent URLs.

The kleptocracy timeline identified this as its biggest QA gap: 4,400+ events created by research agents with no automated verification that sources actually support the claims in event bodies.

## Context

The kleptocracy timeline's existing QA framework includes:
- Structural validation (YAML, required fields, date logic)
- Source quality scoring (tier-1/2/3 distribution)
- Quality auditing (body completeness, source count, metadata)

What's missing:
- URL liveness checks (do source URLs return 200?)
- Content verification (does the source article mention the key claims?)
- Cross-source consistency (do multiple sources agree?)
- Hallucination detection (can claims be independently verified?)

## Scope

### Phase 1: URL Validation
- Add a `pyrite qa check-urls` command that validates all source URLs in a KB
- Check HTTP status codes (200 OK, 301 redirect, 404 not found, etc.)
- Handle rate limiting and timeouts gracefully
- Cache results to avoid re-checking unchanged URLs
- Report: valid, redirected, broken, unreachable URLs per entry
- Support `--fix` to remove broken sources or mark entries for review

### Phase 2: Content Verification (requires LLM)
- Fetch source URL content and extract key claims from the entry body
- Use LLM to compare: "Does this source support these claims?"
- Flag entries where sources don't appear to support key claims
- Store verification results as QA assessment entries
- Support batch processing with cost controls

### Phase 3: Hallucination Detection
- For entries created by AI agents (check provenance.created_by)
- Web search for key claims to find independent corroboration
- Flag entries with no independent verification
- Prioritize high-importance entries (importance >= 8)

## Acceptance Criteria

### Phase 1
- `pyrite qa check-urls --kb=timeline` checks all source URLs
- Broken URLs reported with entry ID and source index
- Results cached (re-run skips already-checked URLs unless `--force`)
- Exits with non-zero status if broken URLs found (CI-friendly)

### Phase 2
- `pyrite qa verify-sources --kb=timeline --sample=50` verifies a sample
- Each entry gets a verification score (0-1) based on source-claim alignment
- Low-scoring entries are flagged for human review
- Cost-controlled: respects `--max-cost` budget parameter

### Phase 3
- `pyrite qa check-hallucinations --kb=timeline --min-importance=8` checks high-priority entries
- Flags entries where web search finds no corroboration for key claims
- Stores results as QA assessment entries with evidence links
