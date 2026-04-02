---
id: qa-phase-2-qa-assessment-entry-type-and-storage
title: 'QA Phase 2: QA Assessment Entry Type and Storage'
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

Subtask of [[qa-agent-workflows]] — Phase 2.

## Problem

QA results need to be stored as first-class KB entries so quality becomes a queryable, trackable property. Without a dedicated entry type, assessment results are ephemeral.

## Solution

Define a `qa_assessment` entry type with schema, link assessments to target entries, and provide query interfaces for assessment state.

## Acceptance Criteria

- `qa_assessment` entry type with schema (target_entry, tier, status, issues_found, issues_resolved, last_assessed)
- Assessments linked to target entries via typed links
- Query interface: entries with open issues, unassessed entries, verification rate by capture lane
- CLI command: `pyrite qa status [--kb <name>]` — dashboard of assessment state
- MCP tool: `kb_qa_status` (read-tier)
- Assessment entries follow the format specified in the parent design

## Dependencies

- Phase 1 (qa-phase-1-tier-1-structural-validation) — structural validation produces the issues that assessments record

## Files Likely Affected

- New or modified: `pyrite/models/qa_types.py` (qa_assessment type)
- Modified: `pyrite/services/qa_service.py` (assessment storage)
- Modified: `pyrite/cli/__init__.py` (qa status command)
- Modified: `pyrite/server/mcp_server.py` (qa status tool)
- New: `pyrite/server/endpoints/qa.py`
