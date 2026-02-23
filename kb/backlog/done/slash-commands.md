---
type: backlog_item
title: "Slash Commands in Editor"
kind: feature
status: done
priority: high
effort: M
tags: [web, editor, ux]
---

Type `/` in the editor to get an inline action menu:

**Built-in commands:**
- `/heading 1-6` — insert heading
- `/callout` — insert callout block (info, warning, tip, etc.)
- `/code` — insert fenced code block
- `/table` — insert table
- `/template` — insert from template (depends on templates-system)
- `/link` — search and insert wikilink
- `/date` — insert current date
- `/divider` — insert horizontal rule
- `/todo` — insert task list

**Implementation:**
- CodeMirror 6 autocomplete extension triggered by `/` at line start
- Tiptap suggestion extension for WYSIWYG mode
- Extensible — plugins can register custom slash commands

Standard in Notion. Essential for discoverability — users don't need to memorize Markdown syntax.
