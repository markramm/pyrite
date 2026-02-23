---
type: backlog_item
title: "Quick Switcher and Command Palette"
kind: feature
status: completed
priority: high
effort: M
tags: [web, navigation, phase-2]
---

Two keyboard-driven navigation features:

**Quick Switcher (Ctrl+O):**
- Modal overlay searching entries via `/api/search`
- Fuzzy matching on title
- Shows entry type icon, KB name, last modified
- Enter to open, Esc to dismiss

**Command Palette (Cmd+K):**
- Action registry with fuzzy-matched command list (fuse.js)
- Built-in actions: new entry, toggle theme, switch KB, open settings, etc.
- Extensible — plugins can register commands

**Global Shortcut Manager:**
- `keyboard.ts` utility for registering/unregistering hotkeys
- Prevents conflicts, supports modifier combos

npm dependency: `fuse.js` for fuzzy matching.
