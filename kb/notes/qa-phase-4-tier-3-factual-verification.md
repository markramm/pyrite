---
id: qa-phase-4-tier-3-factual-verification
title: 'QA Phase 4: Tier 3 Factual Verification'
type: backlog_item
tags:
- feature
- quality
- ai
kind: feature
status: done
priority: medium
effort: L
---

## Parent

Subtask of [[qa-agent-workflows]] — Phase 4.

## Problem

Even with structural and consistency checks, factual accuracy remains unverified. Claims may not match cited sources, dates may be wrong, quotes misattributed, and the KB may contain internal contradictions.

## Solution

A research agent with web search capability that verifies specific claims against cited sources, checks historical accuracy, and detects cross-KB contradictions. Produces confidence-scored factual assessments with source chains.

## Acceptance Criteria

- Research agent with web search for claim verification
- Cross-KB contradiction detection
- Source chain verification (do cited sources actually support the claims?)
- Confidence-scored factual assessments with source provenance
- Checks: claim-source alignment, date accuracy, quote attribution, causal defensibility, statistic verifiability
- CLI command: `pyrite qa verify [--kb <name>] [--entry <id>]`
- Plugin architecture: domain-agnostic core with pluggable evaluation rubrics (legal, scientific, investigative)

## Dependencies

- Phase 3 (qa-phase-3-tier-2-llm-assisted-consistency-checks) — builds on Tier 2 infrastructure
- Web search capability

## Files Likely Affected

- Modified: `pyrite/services/qa_service.py` (Tier 3 verification logic)
- New: verification agent module with web search integration
- Modified: `pyrite/server/mcp_server.py` (qa verify tool)
- Modified: `pyrite/cli/__init__.py` (qa verify command)
