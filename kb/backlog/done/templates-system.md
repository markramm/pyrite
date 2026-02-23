---
type: backlog_item
title: "Templates System"
kind: feature
status: completed
priority: high
effort: M
tags: [web, editor, workflow]
---

User-defined templates for entry creation:

- Template files stored in KB (e.g., `_templates/meeting-note.md`, `_templates/research-brief.md`)
- Template variables: `{{date}}`, `{{title}}`, `{{kb}}`, `{{author}}`
- Template picker shown when creating new entry (or via slash command)
- Default templates per entry type (configurable in settings)
- Templates are just Markdown files — editable in the same editor

Both Obsidian (Templater plugin / core Templates) and Notion treat templates as essential. The daily notes template (Phase 3) should use this same system.

Prerequisite: None (can be built independently of phases).
