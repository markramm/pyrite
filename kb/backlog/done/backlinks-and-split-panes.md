---
type: backlog_item
title: "Backlinks Panel and Split Panes"
kind: feature
status: completed
priority: high
effort: M
tags: [web, editor, phase-2]
---

**Backlinks Panel:**
- Sidebar panel showing all entries that link to the current entry
- Uses existing `/api/entries/{id}` backlinks data
- Each backlink shows title, snippet of linking context, entry type
- Click to navigate

**Split Panes:**
- CSS Grid-based resizable split pane component
- Two entries side-by-side, or editor + preview
- Drag handle for resizing
- Keyboard shortcut to toggle split

These complete the Phase 2 "knowledge tool" feel — users can see connections and work with multiple entries simultaneously.
