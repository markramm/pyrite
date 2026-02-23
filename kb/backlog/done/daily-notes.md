---
type: backlog_item
title: "Daily Notes with Calendar Navigation"
kind: feature
status: completed
priority: high
effort: M
tags: [web, workflow, phase-3]
---

Daily notes workflow inspired by Obsidian:

**Backend:**
- `GET /api/daily/{date}` — get or auto-create daily note from template
- Template stored in settings/config

**Frontend:**
- `DailyNote.svelte` — today's note with editor
- `Calendar.svelte` — mini calendar for date navigation, dots indicate notes exist
- Cmd+D shortcut to open today's daily note
- Auto-creates from template if doesn't exist
- Previous/next day navigation

Daily notes are the entry point for many PKM workflows — capture thoughts, then refactor into permanent notes.
