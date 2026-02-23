---
type: backlog_item
title: "Investigation Skill for Claude Code"
kind: feature
status: proposed
priority: high
effort: L
tags: [ai, claude-code, research, workflow]
---

A Claude Code skill for journalist-style entity investigation:

**Methodology:** Identify → Collect → Map → Track → Assess

**Process:**
1. **Identify entity** — Person, organization, event, or topic under investigation
2. **Collect mentions** — Search all KBs for references, create person/org entries if missing
3. **Map relationships** — Use backlinks and graph to find connections, create relationship entries
4. **Track source chain** — Every claim links to a source entry, note provenance
5. **Assess confidence** — Rate findings by source quality and corroboration

**Implementation:**
- `skills/investigation/SKILL.md` — main skill with hard gates on source tracking
- `skills/investigation/entity-profile-template.md` — template for entity profiles
- `skills/investigation/relationship-mapping.md` — guide for connection documentation
- Uses `pyrite search`, `pyrite backlinks`, `pyrite timeline` for KB queries
- Creates TaskCreate items for each entity/relationship to track

**Command:** `/investigate <entity>` invokes this skill.

**Key differentiator:** This makes Pyrite a genuine research tool, not just a note app. The source chain requirement is what separates investigative research from casual note-taking.
