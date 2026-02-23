---
type: backlog_item
title: "Git-Based Version History"
kind: feature
status: proposed
priority: medium
effort: M
tags: [web, git, phase-5]
---

Leverage git history for entry version tracking:

**Backend:**
- `GET /api/entries/{id}/versions` — list commits touching this entry's file
- Returns commit hash, date, author, diff summary
- `GET /api/entries/{id}/versions/{hash}` — get entry content at specific commit

**Frontend:**
- Version history panel in entry view
- Side-by-side diff view
- Restore to previous version

Unique differentiator vs Notion/Obsidian — Pyrite's git-native storage provides free, unlimited version history with full diffs.
