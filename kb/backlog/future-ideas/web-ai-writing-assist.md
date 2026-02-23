---
type: backlog_item
title: "Web UI AI: Writing Assistant in Editor"
kind: feature
status: proposed
priority: low
effort: L
tags: [ai, web, editor]
---

AI-powered writing assistance directly in the editor:

**Features:**
- Select text → context menu: Summarize, Expand, Rewrite, Simplify, Continue
- `POST /api/ai/assist` — sends selected text + action + surrounding context
- Streaming inline replacement/insertion
- Undo support (Cmd+Z reverts AI changes)

**Editor Integration:**
- CodeMirror 6: custom decoration for AI-generated text (subtle highlight until accepted)
- Tiptap: custom extension for inline AI suggestions
- Keyboard shortcut: Cmd+Shift+A to open AI assist on selection

**Also:**
- "Generate entry from prompt" — modal where user describes what they want, AI creates full entry
- `POST /api/ai/generate` — returns structured entry with frontmatter

**Depends on:** llm-abstraction-service, tiptap-wysiwyg-editor (for Tiptap integration)
