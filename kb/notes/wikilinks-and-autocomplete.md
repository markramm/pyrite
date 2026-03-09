---
id: wikilinks-and-autocomplete
title: "Wikilinks with Autocomplete in Editor"
type: backlog_item
tags: [web, editor, phase-2]
kind: feature
status: done
priority: high
effort: L
---

Implement `[[wikilink]]` support in CodeMirror 6:

- `[[` triggers autocomplete dropdown via `/api/entries/titles` endpoint
- Wikilinks render as styled clickable pills in live preview (hidden syntax when cursor is outside)
- Click navigates to the linked entry
- Support `[[id|display text]]` syntax
- New backend endpoints: `GET /api/entries/titles` (lightweight autocomplete), `GET /api/entries/resolve` (wikilink target resolution)
- Shared wikilink parsing utilities (`wikilink-utils.ts`)

This is the foundational linking feature — everything else (backlinks, graph, block refs) builds on it.

## Completed

Implemented in commit `46ea1d6`. Backend: `GET /api/entries/titles` with kb/query/limit filtering and `GET /api/entries/resolve` with ID-first then title fallback. Frontend: CodeMirror 6 `wikilinkExtension()` with async autocomplete on `[[`, `WikilinkWidget` pill decorations with cursor-aware hiding, 30s title cache. Shared `wikilink-utils.ts` for parsing and HTML rendering. 13 backend tests + 11 frontend tests.
