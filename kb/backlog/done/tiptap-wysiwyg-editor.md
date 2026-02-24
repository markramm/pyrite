---
type: backlog_item
title: "Tiptap WYSIWYG Editor Mode"
kind: feature
status: done
priority: medium
effort: L
tags: [web, editor, phase-4]
---

Dual editor system — toggle between CodeMirror (source) and Tiptap (WYSIWYG):

**Tiptap Setup:**
- StarterKit, Link, TaskList, TaskItem, Placeholder extensions
- Custom wikilink Node (inline, suggestion-triggered)
- Markdown serialization/deserialization

**Toggle Mechanism:**
- Shared canonical Markdown string in Svelte store
- On toggle: read markdown from active editor → update store → mount other editor
- No intermediate format — Markdown is always the source of truth
- Toggle button in toolbar

**Wikilinks in Tiptap:**
- Custom inline Node type
- Suggestion/autocomplete triggered by `[[`
- Same styling as CodeMirror pills

npm dependencies: `@tiptap/core`, `@tiptap/starter-kit`, `@tiptap/extension-link`, `@tiptap/extension-placeholder`, `@tiptap/extension-task-list`, `@tiptap/extension-task-item`, `@tiptap/pm`
