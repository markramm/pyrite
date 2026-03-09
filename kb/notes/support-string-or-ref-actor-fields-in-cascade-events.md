---
id: support-string-or-ref-actor-fields-in-cascade-events
title: Support string-or-ref actor fields in Cascade events
type: backlog_item
tags:
- cascade
- actors
- migration
- schema
links:
- target: epic-migrate-kleptocracy-timeline-to-pyrite-managed-kb
  relation: subtask_of
  kb: pyrite
- target: actor-extraction-and-migration-tool-for-cascade-timelines
  relation: blocks
  kb: pyrite
- target: backlink-indexing-for-string-based-actor-references
  relation: blocks
  kb: pyrite
kind: feature
status: accepted
priority: high
effort: L
---

## Problem

The Cascade plugin's `cascade_event` type currently expects actors as either plain strings or entry references, but not both in the same field. The kleptocracy timeline project uses plain string actor names (e.g., `- Donald Trump`) in its 4,400+ event files. Migrating to Pyrite requires supporting a transition period where actors can be either:

1. Plain strings: `- Donald Trump`
2. Wikilinks to actor entries: `- [[donald-trump]]`

Both must resolve correctly for backlinks, search, and the knowledge graph.

## Context

The kleptocracy timeline at capturecascade.org has 4,400+ events with ~1,235 unique actor names referenced ~7,780 times. Converting all at once is impractical. The system needs to handle mixed references gracefully during a migration period, and potentially long-term for ease of use.

## Scope

- Modify the Cascade event schema to accept actors as either strings or wikilinks
- String actors should be resolved to actor entries via title + aliases matching
- Backlinks should work for both string and wikilink actor references
- The index should track string-based actor references for search and graph purposes
- Validation should warn (not error) when string actors have no matching entry, suggesting entry creation
- Export/API should normalize both formats to a consistent output

## Acceptance Criteria

- Events with `actors: ["Donald Trump"]` and `actors: ["[[donald-trump]]"]` both resolve to the same actor entry
- Backlinks from actor entries show all events referencing that actor (by string or wikilink)
- `pyrite search --type=cascade_event --field actors="Donald Trump"` returns correct results regardless of reference format
- QA validation warns on unresolved string actors but does not block
- Mixed formats within a single event's actor list are supported
