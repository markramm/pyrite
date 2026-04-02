---
id: epic-web-ui-feature-parity
title: "Epic: Web UI Feature Parity with Backend API"
type: backlog_item
tags: [web, ux, epic]
kind: epic
status: done
priority: high
effort: XL
---

## Problem

The web UI exposes roughly 45% of backend API capabilities. Key features like entry metadata editing, git operations, advanced search filters, the review system, and bulk operations are CLI/API-only. This limits the value of the web UI for both demo visitors and installed users.

## Scope

This epic tracks closing the gap between what the backend can do and what the web UI surfaces. Grouped into phases by impact.

### Phase 1: Entry Experience (high impact, demo-visible)

- [[web-ui-entry-metadata-display]] — Show importance, status, date, sources, participants, custom metadata on entry pages
- [[web-ui-entry-creation-fields]] — Add date picker, importance slider, status selector, sources, custom fields to entry creation/edit
- [[web-ui-orient-in-sidebar]] — Add orient page to sidebar navigation
- [[web-ui-wikilink-rendering-in-lists]] — Render wikilinks as clickable links in entry list snippets

### Phase 2: Search and Discovery (high impact)

- [[web-ui-advanced-search-filters]] — Date range picker, tag multi-select, field projection, query expansion toggle
- [[web-ui-saved-searches]] — Save and recall search queries
- [[web-ui-graph-centrality]] — Activate betweenness centrality visualization in graph view

### Phase 3: Git and Admin (critical for installed users)

- [[web-ui-git-operations]] — Commit, push, diff, and sync from the web UI
- [[web-ui-index-management]] — Rebuild/sync index, view index stats, embedding status
- [[web-ui-bulk-operations]] — Bulk tag, bulk move, bulk delete, bulk status change

### Phase 4: QA and Reviews (knowledge quality)

- [[web-ui-review-system]] — Surface the review system (create, list, evaluate reviews)
- [[web-ui-qa-enhancements]] — Rule-based filtering, auto-fix, issue acknowledgment, historical trends

### Phase 5: Collaboration and Integration

- [[web-ui-daily-notes-calendar]] — Calendar view for daily notes
- [[web-ui-collection-editing]] — View config, query builder, collection CRUD
- [[web-ui-user-management]] — Permission management, user roles, KB access control
- [[web-ui-webhook-config]] — Webhook/integration configuration

## Success criteria

- All entry fields visible and editable in the web UI
- Search page exposes all backend filtering capabilities
- Git operations accessible without CLI
- Review system visible and usable
- Bulk operations available for common tasks
