---
id: source-url-validation-and-content-verification-for-qa
title: 'Source URL liveness checking for QA (Phase 1)'
type: backlog_item
tags:
- qa
- sources
- validation
- cascade
links:
- target: epic-migrate-kleptocracy-timeline-to-pyrite-managed-kb
  relation: subtask_of
  kb: pyrite
- target: source-content-verification-via-llm
  relation: blocks
  kb: pyrite
- target: ai-hallucination-detection-for-research-kbs
  relation: blocks
  kb: pyrite
kind: feature
status: done
assignee: claude
effort: M
---

## Problem

Pyrite's QA service validates structural aspects of entries (required fields, date formats, schema compliance) but does not verify that source URLs are valid. This is a significant gap for research KBs where entries are created by AI agents that may cite non-existent URLs.

The kleptocracy timeline identified this as its biggest QA gap: 4,400+ events created by research agents with no automated verification that source URLs are live.

## Context

The kleptocracy timeline's existing QA framework includes:
- Structural validation (YAML, required fields, date logic)
- Source quality scoring (tier-1/2/3 distribution)
- Quality auditing (body completeness, source count, metadata)

What's missing: URL liveness checks (do source URLs return 200?).

## Scope

- Add a `pyrite qa check-urls` command that validates all source URLs in a KB
- Check HTTP status codes (200 OK, 301 redirect, 404 not found, etc.)
- Handle rate limiting and timeouts gracefully (configurable concurrency, per-domain rate limits)
- Cache results to avoid re-checking unchanged URLs (SQLite or file-based cache with TTL)
- Report: valid, redirected, broken, unreachable URLs per entry
- Support `--fix` to remove broken sources or mark entries for review
- Support `--sample=N` to check a random sample (useful for large KBs)

## Acceptance Criteria

- `pyrite qa check-urls --kb=timeline` checks all source URLs
- Broken URLs reported with entry ID and source index
- Results cached (re-run skips already-checked URLs unless `--force`)
- Exits with non-zero status if broken URLs found (CI-friendly)
- Rate limiting prevents being blocked by target sites
- `--fix` marks entries with broken URLs for review (adds tag or status)
