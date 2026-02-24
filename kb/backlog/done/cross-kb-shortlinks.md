---
type: backlog_item
title: "Cross-KB Shortlinks"
kind: feature
status: done
priority: high
effort: L
tags: [linking, cross-kb, wikilinks, core]
---

Add `[[kb-shortname:target-id]]` syntax for cross-KB wikilinks, inspired by Apache Allura's shortlink system.

## Problem

Currently `[[target-id]]` resolves within the current KB only. There's no way to link from an architectural decision in the `pyrite` KB to a Svelte pattern in the `svelte` KB, or from a backlog item to a component in another project's KB.

## Design

### Shortname Directory

Each KB gets a configurable shortname (defaults to its name). Stored in `kb.yaml`:

```yaml
name: svelte
shortname: sv     # optional, defaults to kb name
```

The shortname registry is derived from the config — no separate directory table needed.

### Syntax

- `[[sv:svelte-5-runes-state]]` — link to entry in the `svelte` KB using shortname `sv`
- `[[pyrite:adr-001]]` — link using full KB name (always works)
- `[[target-id]]` — existing behavior, resolves in current KB

### Resolution

Extend `resolve_entry()` to parse the `prefix:id` format:
1. Split on first `:` — if prefix matches a KB shortname or name, resolve in that KB
2. Otherwise treat the whole string as an entry ID in the current KB (preserves backward compat)

### Indexing

The existing body wikilink indexer (`_WIKILINK_RE` in `index.py`) already extracts targets. Extend it to:
- Parse `kb:id` format and set `target_kb` accordingly
- Store cross-KB links in the `link` table with correct `target_kb`

### Frontend

- `renderWikilinks()` — detect `kb:id` format, generate href to `/entries/{id}?kb={kb_name}`
- CodeMirror autocomplete — after typing `[[kb:`, filter completions to entries in that KB
- Tiptap extension — same cross-KB awareness

### Batch resolve

`POST /entries/resolve-batch` already exists. Extend to accept `kb:id` format in targets array.

## Prior Art

Apache Allura used `[[app:artifact-id]]` (e.g. `[[bug:123]]`, `[[wiki:PageName]]`, `[[commit:abc123]]`) to link across tracker, wiki, git, IRC, and other tools within a project. Every artifact type had a shortname, making cross-tool linking seamless. This was highly valuable in practice for connecting discussions to code to tickets.

## Depends On

- Wikilink body indexing (completed)
- Batch resolve endpoint (completed)
