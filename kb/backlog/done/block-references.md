---
type: backlog_item
title: "Block References and Transclusion"
kind: feature
status: retired
priority: high
effort: XL
tags: [web, editor, linking]
---

Reference and embed specific sections from other entries:

**Syntax:**
- `![[entry#section]]` — embed/transclude a heading section
- `![[entry^block-id]]` — embed a specific block
- `[[entry#section]]` — link to a specific section (no embed)

**Implementation:**
- Auto-generate block IDs (append `^abc123` to paragraphs when referenced)
- Transclusion renders referenced content inline (read-only, with source link)
- Editor decorations show embedded content in live preview
- Backend support for resolving block references

**Depends on:** wikilinks-and-autocomplete

Core Obsidian feature that enables atomic note-taking and Zettelkasten method beyond basic page-level links.
