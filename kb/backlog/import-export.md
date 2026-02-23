---
type: backlog_item
title: "Import/Export Support"
kind: feature
status: proposed
priority: medium
effort: L
tags: [api, migration, dx]
---

Migration paths for adoption and data portability:

**Import from:**
- Obsidian vault (direct — both are Markdown with YAML frontmatter, map `[[wikilinks]]`)
- Notion export (HTML/Markdown zip — parse and convert)
- CSV (bulk import with column mapping)
- Plain Markdown directory

**Export to:**
- Markdown zip (already native format)
- JSON (structured export of all entries + metadata)
- PDF (single entry, rendered)

**Implementation:**
- `POST /api/import` endpoint with file upload
- Import wizard in web UI (select source, preview, confirm)
- `GET /api/export` endpoint with format parameter
- Progress indicator for large imports

Critical for adoption — users won't switch without a migration path. Pyrite's Markdown-native format is an advantage for Obsidian migration.
