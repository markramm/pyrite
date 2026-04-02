---
id: ji-ui-investigation-dashboard
title: Investigation dashboard with claims coverage and gap detection
type: backlog_item
tags:
- journalism
- investigation
- web
- frontend
- dashboard
links:
- target: epic-investigation-ui-views
  relation: subtask_of
  kb: pyrite
kind: feature
status: proposed
priority: high
effort: M
---

## Problem

When a journalist returns to an investigation after time away, they need to quickly answer: "Where was I? What's done? What's missing? What changed?" The dashboard is the investigation's home page.

## Scope

### Investigation Overview
- Investigation title, subject, scope, status, lead reporter
- Key metrics: total events, entities, claims, sources, connections
- Creation date, last activity, activity trend

### Claims Status
- Breakdown: unverified / partially verified / corroborated / disputed / retracted
- Progress bar showing verification coverage
- List of stale unverified claims (unverified > 7 days)
- Recently updated claims

### Evidence Gaps
- Claims with no linked evidence
- Evidence entries with no source document
- Source documents with broken/unchecked URLs
- Entities mentioned in events but with no dedicated entry

### Activity Feed
- Recent entries created/modified (last 7/30 days)
- Recent MCP tool invocations (what the agent did)
- Review activity (claims verified, sources checked)

### Quick Actions
- "Continue research" — opens most recent unverified claim context
- "Check sources" — runs URL validation on unchecked sources
- "Review claims" — opens oldest unverified claims for review
- "Add event" — quick-create investigation event

## Acceptance Criteria

- Dashboard loads in <2s for investigations with 1,000+ entries
- Claims status reflects real-time state
- Evidence gap detection surfaces actionable items
- Activity feed shows last 30 days by default
- Quick actions work and link to correct views
