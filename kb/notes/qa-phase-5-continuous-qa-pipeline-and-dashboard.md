---
id: qa-phase-5-continuous-qa-pipeline-and-dashboard
title: 'QA Phase 5: Continuous QA Pipeline and Dashboard'
type: backlog_item
tags:
- feature
- quality
- ai
kind: feature
effort: L
---

## Parent

Subtask of [[qa-agent-workflows]] — Phase 5.

## Problem

QA evaluations are ad hoc. Without a continuous pipeline, quality degrades over time as new entries skip review and old entries go stale. There is no visibility into overall KB health.

## Solution

Automated pipeline that triggers Tier 1 on save (partially done), schedules batch Tier 2/3 runs, and surfaces results in a web dashboard.

## Acceptance Criteria

- ~~Post-save hook triggers Tier 1 validation automatically~~ **Already done**: `validate` param on `kb_create`/`kb_update` MCP tools + `qa_on_write: true` KB setting
- Scheduled batch runs for Tier 2/3 (configurable frequency)
- QA dashboard in web UI: verification rates, issue trends, coverage gaps
- "Entries needing review" virtual collection with QA-based query
- Integration with existing hooks system and collections

## Dependencies

- Phase 2 (qa-phase-2-qa-assessment-entry-type-and-storage) — assessment entries must exist
- Hooks system (done)
- Collections (done)
- Capture lane validation

## Files Likely Affected

- Modified: `pyrite/services/qa_service.py` (batch scheduling)
- New: `web/src/routes/qa/` (dashboard UI)
- Modified: web frontend for QA views
- Modified: `pyrite/server/endpoints/qa.py` (dashboard API)
