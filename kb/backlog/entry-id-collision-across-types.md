---
id: entry-id-collision-across-types
type: backlog_item
title: "Bug: Entry ID collisions across types cause silent index overwrites"
kind: bug
status: proposed
priority: high
effort: M
tags: [storage, indexing, bug, data-integrity]
---

# Bug: Entry ID collisions across types cause silent index overwrites

## Problem

Entry IDs are generated from titles without namespacing by entry type. When an ADR and a backlog item have similar titles, they generate the same ID and the last-indexed entry silently overwrites the first via `upsert_entry`.

### Affected entries (known)

| ADR file | Generated ID | Overwrites |
|---|---|---|
| `kb/adrs/0010-content-negotiation...` | `content-negotiation-and-multi-format-support` | `kb/backlog/done/content-negotiation-and-formats.md` |
| `kb/adrs/0012-block-references...` | `block-references-and-transclusion` | `kb/backlog/done/block-references.md` |
| `kb/adrs/0017-entry-protocol-mixins` | `entry-protocol-mixins` | `kb/backlog/done/entry-protocol-mixins.md` |

### Impact

- 3 ADRs missing from index despite files existing on disk
- `index health` reports 0 unindexed files (false negative)
- `sw adrs` shows 14/17 ADRs
- Any future entries with similar titles will collide

## Root cause

`Entry.__init__` generates `self.id` from `slugify(title)` without incorporating `entry_type`. The `entry` table uses `id` as the primary key with no composite key on `(id, entry_type)`.

## Proposed fix options

1. **Prefix IDs with type**: `adr-content-negotiation...` vs `backlog-content-negotiation...` — breaks existing IDs, needs migration
2. **Composite primary key**: change `entry` table PK to `(id, kb_name)` or `(id, entry_type)` — large schema change
3. **Detect and suffix on collision**: during indexing, if ID exists with different type, append `-adr`, `-backlog`, etc. — fragile
4. **Use explicit `id` from frontmatter**: ADRs already have `adr_number`, backlog items have `id` in frontmatter. Prefer frontmatter `id` over title-derived slug — minimal change, backwards compatible

Option 4 is recommended: when frontmatter contains an explicit `id` field, use it as-is. The backlog items already have explicit IDs (e.g., `id: entry-protocol-mixins`). ADRs could use `adr-0017` format.

## Files to modify

- `pyrite/models/base.py` — `Entry.__init__` ID generation
- `pyrite/storage/index.py` — `_entry_to_dict` ID handling
- `kb/adrs/*.md` — add explicit `id` fields to ADR frontmatter
