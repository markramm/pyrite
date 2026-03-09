---
id: qa-phase-3-tier-2-llm-assisted-consistency-checks
title: 'QA Phase 3: Tier 2 LLM-Assisted Consistency Checks'
type: backlog_item
tags:
- feature
- quality
- ai
kind: feature
effort: L
---

## Parent

Subtask of [[qa-agent-workflows]] — Phase 3.

## Problem

Structural validation (Tier 1) catches missing fields but not semantic issues: importance score inconsistencies, inappropriate tags, body-title mismatches, near-duplicates, or editorial guideline drift. These require AI judgment.

## Solution

LLM-based evaluation using type-level AI instructions (from CORE_TYPE_METADATA) and KB-level editorial guidelines. Produces confidence-scored assessments stored as qa_assessment entries.

## Acceptance Criteria

- LLM evaluation prompts using type AI instructions + KB editorial guidelines
- Consistency scoring against comparable entries (semantic similarity to find comparables)
- Checks: body supports title claim, importance score consistency, tag/lane appropriateness, contextualization quality, bidirectional relationships, summary accuracy, near-duplicate detection
- Confidence-scored assessments with 0.0-1.0 scores
- CLI command: `pyrite qa assess [--kb <name>] [--entry <id>] [--tier 2]`
- MCP tool: `kb_qa_assess` (write-tier, creates assessment entries)
- KB-level editorial guidelines support via new optional `editorial_guidelines` section in `kb.yaml`

## Dependencies

- Phase 2 (qa-phase-2-qa-assessment-entry-type-and-storage) — assessment entry type must exist
- LLM abstraction service (done)
- Type metadata (done)

## Files Likely Affected

- Modified: `pyrite/services/qa_service.py` (Tier 2 evaluation logic)
- Modified: `pyrite/config.py` (editorial_guidelines in KBConfig)
- Modified: `pyrite/cli/__init__.py` (qa assess command)
- Modified: `pyrite/server/mcp_server.py` (qa assess tool)
