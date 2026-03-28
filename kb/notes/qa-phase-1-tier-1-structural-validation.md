---
id: qa-phase-1-tier-1-structural-validation
title: 'QA Phase 1: Tier 1 Structural Validation'
type: backlog_item
tags:
- feature
- quality
- ai
kind: feature
status: done
effort: M
---

## Parent

Subtask of [[qa-agent-workflows]] — Phase 1.

## Problem

No automated structural validation exists for KB entries. Missing fields, malformed dates, broken wikilinks, and orphaned tags go undetected after creation.

## Solution

Implement deterministic, non-LLM validation that checks entries against their type schemas.

## Acceptance Criteria

- `QAService` with `validate_entry()` and `validate_all()` methods in `pyrite/services/qa_service.py`
- Validation rules derived from schema + type metadata per entry type
- Checks: required fields, date formats, importance range, controlled vocabulary, tag existence, wikilink resolution, source URLs/citations, non-empty bodies
- CLI command: `pyrite qa validate [--kb <name>] [--entry <id>] [--fix]`
- MCP tool: `kb_qa_validate` (read-tier)
- Output: structured issue list with field, severity, and message
- No LLM dependency — pure Python validation

## Dependencies

None — pure validation against existing schema.

## Files Likely Affected

- New: `pyrite/services/qa_service.py` (QAService class)
- New: `pyrite/models/qa_types.py` (issue/result models)
- Modified: `pyrite/cli/__init__.py` (new `qa` command group)
- Modified: `pyrite/server/mcp_server.py` (new QA tool)
- New: `tests/test_qa_service.py`
