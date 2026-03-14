---
id: auto-inverse-links-for-bidirectional-relationships
title: Auto-generate inverse links for known bidirectional relationship types
type: backlog_item
tags:
- core
- graph
- relationships
- ux
- plugin-driven
links:
- target: adr-0022
  relation: informed_by
  kb: pyrite
- target: typed-relationship-entries-as-first-class-entities
  relation: related_to
  kb: pyrite
kind: improvement
status: done
priority: high
effort: M
---

## Problem

Pyrite's relationship type registry defines bidirectional pairs (`subtask_of`/`has_subtask`, `depends_on`/`depended_on_by`, `blocks`/`blocked_by`, etc.). Currently, creating a bidirectional link requires editing **both** entries:

```yaml
# Entry A: must add this
links:
- target: entry-b
  relation: subtask_of

# Entry B: must ALSO add this
links:
- target: entry-a
  relation: has_subtask
```

This causes three problems:

1. **Agent errors** — agents frequently add one side and forget the other, leaving the graph inconsistent. This was observed repeatedly during backlog refinement sessions.
2. **Wasted tokens** — two tool calls (read + edit on each entry) to express one relationship. For bulk operations (creating an epic with 7 subtasks), that's 14 extra tool calls.
3. **Consistency risk** — if one save fails or the agent is interrupted between the two edits, the graph has a dangling half-link.

## Solution

Apply the same index-only pattern from ADR-0022 (edge-entities): the inverse link is **derived at index time**, not stored in frontmatter.

When entry A has `links: [{target: entry-b, relation: subtask_of}]`, the index automatically generates the inverse: entry B has a backlink from entry A with relation `has_subtask`. No edit to entry B's frontmatter needed.

### How it works

1. Relationship type registry already knows inverse pairs (e.g., `subtask_of` ↔ `has_subtask`)
2. During index sync, for each link with a known inverse, store the inverse in the index
3. `pyrite backlinks entry-b` returns the auto-generated inverse alongside explicit links and wikilinks
4. Backlinks output labels these as `link_inverse:` to distinguish from explicit `link:` entries

### What changes for agents and users

**Before (two edits):**
```
1. Edit entry-a: add link subtask_of → entry-b
2. Edit entry-b: add link has_subtask → entry-a
```

**After (one edit):**
```
1. Edit entry-a: add link subtask_of → entry-b
   (inverse has_subtask auto-generated in index)
```

### What changes for existing data

- Existing entries with both sides explicitly written continue to work (no migration needed)
- The index deduplicates: if both sides exist in frontmatter AND the inverse is auto-generated, the backlinks output shows it once
- Over time, agents and users can stop writing the inverse side — the explicit inverse becomes optional

### Backlinks output with four source types

```
$ pyrite backlinks entry-b
  entry-a              (link_inverse: has_subtask)    # auto-generated inverse
  ownership-x-y        (edge: ownership.asset)        # edge-entity endpoint
  some-note            (link: relates_to)              # explicit frontmatter link
  article-z            (wikilink)                      # body wikilink
```

## Impacted Files

- `pyrite/storage/database.py` — generate inverse links during index sync
- `pyrite/storage/queries.py` — include inverse links in backlinks queries
- `pyrite/services/graph_service.py` — traverse inverse links in graph queries
- Relationship type registries (core + plugins) — already define inverse pairs, no changes needed

## Relationship to ADR-0022

This is the simpler sibling of edge-entities. Both use index-only derived relationships:
- **Edge-entities** → rich relationships with properties (ownership with percentage)
- **Auto-inverse links** → simple relationships without properties (subtask_of/has_subtask)

Both eliminate the need to manually maintain both sides of a bidirectional relationship. Together they cover the full spectrum from simple references to property-rich connections.

## Acceptance Criteria

- Adding `subtask_of → entry-b` on entry A auto-generates `has_subtask` backlink on entry B in the index
- `pyrite backlinks` includes auto-generated inverses, labeled as `link_inverse:`
- Agents only need one edit to create a bidirectional relationship
- Existing entries with both sides explicitly written show no duplicates in backlinks
- Graph service traverses auto-generated inverses correctly
- Works for all relationship types with known inverses (core + plugin-defined)
- `pyrite index sync` rebuilds all auto-generated inverses
