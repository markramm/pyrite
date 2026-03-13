---
id: ji-investigation-guided-setup
title: Investigation guided setup and context rebuilding
type: backlog_item
tags:
- journalism
- investigation
- workflow
- ux
links:
- target: epic-core-journalism-investigation-plugin
  relation: depends_on
  kb: pyrite
kind: feature
status: done
assignee: claude
effort: S
---

## Problem

Starting a new investigation and returning to an existing one are both friction points. New investigations need guided setup (what's the scope? who are the initial subjects?). Returning investigations need fast context rebuild ("where was I?").

## Scope

### New Investigation Setup
- `pyrite investigation start` — interactive guided setup
- Prompts: investigation title, subject/scope, key questions, initial entities to research
- Creates: investigation entry, initial person/org entries, first research tasks
- Suggests: related entries from known-entities KB and prior investigations
- MCP tool: `investigation_start` — same flow for agent-initiated investigations

### Context Rebuild ("Where Was I?")
- `pyrite investigation status <investigation-id>` — comprehensive status report
- Shows: last activity, recent changes, unverified claims, evidence gaps, stale research threads
- MCP tool: `investigation_status` — returns structured context for agent to continue work
- Designed for the iterative workflow: research → build → verify → restructure → research again

### Investigation Restructuring
- `pyrite investigation restructure` — tools for re-organizing an investigation
- Re-link events to different themes
- Split investigation into sub-investigations
- Promote/demote entity importance
- Archive completed threads while keeping active ones visible

## Acceptance Criteria

- New investigation setup creates a usable starting point in <2 minutes
- Status report answers "where was I?" for investigations idle >7 days
- Restructuring operations preserve all links and source attribution
- Both CLI and MCP tool interfaces work
