---
type: backlog_item
title: "Claude Code Plugin Manifest and Structure"
kind: feature
status: completed
priority: high
effort: S
tags: [ai, claude-code, dx]
---

Create a proper Claude Code plugin for Pyrite:

```
.claude-plugin/
  plugin.json              # Plugin manifest (name, version, description)
  plugin.md                # Global context for skill discovery
```

**plugin.json** registers:
- Plugin metadata (name: pyrite, version, author)
- Auto-discovery of skills/, commands/, hooks/

**plugin.md** provides:
- Project overview for Claude Code context
- Skill discovery guidance (when to use each skill)
- Link to kb/ for deeper project knowledge

This is the scaffolding that makes all other Claude Code skills/commands discoverable. Small effort — just two config files.

## Completed

Implemented in commit `46ea1d6`. Created `.claude-plugin/plugin.json` with autoDiscover for skills, commands, hooks, and agents. Created `.claude-plugin/plugin.md` with project overview, key commands, skill listing, and technology stack table.
