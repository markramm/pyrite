---
id: obsidian-migration
title: "Obsidian Vault Migration / Import"
type: backlog_item
tags:
- feature
- import
- obsidian
- pkm
kind: feature
priority: low
effort: M
status: planned
links:
- pkm-capture-plugin
- launch-plan
---

## Problem

Many potential Pyrite users (especially PKM users) have existing Obsidian vaults with hundreds or thousands of notes. Migrating to Pyrite requires converting Obsidian's conventions (YAML frontmatter, wikilinks, callouts, dataview queries, folder structure) into Pyrite's type system. Without a migration path, these users face a cold start — they'd lose years of accumulated knowledge.

## Solution

An import command that reads an Obsidian vault and creates a Pyrite KB from it, preserving as much structure as possible.

### What Needs Mapping

| Obsidian Feature | Pyrite Equivalent | Complexity |
|-----------------|-------------------|------------|
| YAML frontmatter | Pyrite frontmatter (mostly compatible) | Low |
| `[[wikilinks]]` | `[[wikilinks]]` (already compatible) | Low |
| `[[wikilink\|alias]]` | Supported | Low |
| Tags (`#tag`, `#nested/tag`) | Tags (nested tags supported) | Low |
| `> [!callout]` blocks | Callout blocks (already compatible) | Low |
| Folder structure | KB subdirectories | Low |
| Dataview queries | Collections with query DSL (partial) | Medium |
| Canvas files | Not supported (future canvas feature) | Deferred |
| Community plugins (Templater, etc.) | Not directly mappable | Deferred |
| Attachments (images, PDFs) | Copy to KB, update references | Medium |

### Usage

```bash
# Basic migration
pyrite init --from-obsidian /path/to/vault --path ./my-kb

# With type inference (AI-assisted)
pyrite init --from-obsidian /path/to/vault --infer-types --path ./my-kb

# Dry run to preview what would be created
pyrite init --from-obsidian /path/to/vault --dry-run
```

### Type Inference (optional, AI-assisted)

For vaults with consistent frontmatter, Pyrite can infer types from the data:
- Notes with `date` and `rating` fields → likely reviews
- Notes with `author` and `isbn` → likely book notes
- Notes with `status` and `priority` → likely tasks/todos

This is optional — without it, all notes import as the base `note` type with their original frontmatter preserved.

## Prerequisites

- Import/export support (#36, already done) provides the foundation
- PKM capture plugin (wave 4) is the broader context, but migration can ship independently

## Success Criteria

- `pyrite init --from-obsidian <vault>` creates a working KB from a real Obsidian vault
- Wikilinks, tags, callouts, and frontmatter preserved
- Attachments copied and references updated
- No data loss — original vault untouched
- 1000-note vault imports in under 30 seconds

## Launch Context

Could ship as early as wave 1 (0.8 alpha) as a PKM onramp, or bundle with wave 4 (PKM capture plugin). Standalone migration is lower effort than the full PKM plugin and provides immediate value to Obsidian users evaluating Pyrite.
