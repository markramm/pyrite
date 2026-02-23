---
type: backlog_item
title: "Settings Page and User Preferences"
kind: feature
status: proposed
priority: medium
effort: M
tags: [web, ux, phase-4]
---

Persistent user preferences:

**Backend:**
- `GET /api/settings` + `PUT /api/settings` — stored in SQLite
- Settings schema with defaults

**Frontend:**
- `/settings` route with sections:
  - Appearance: theme, font size, editor font
  - Editor: default mode (CM vs Tiptap), vim keybindings toggle
  - Daily notes: template, default KB
  - General: default KB, items per page

Settings persist across sessions and browser refreshes.
