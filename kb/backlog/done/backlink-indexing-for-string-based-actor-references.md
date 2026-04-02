---
id: backlink-indexing-for-string-based-actor-references
title: Backlink indexing for string-based actor references
type: backlog_item
tags:
- cascade
- actors
- index
- backlinks
- search
links:
- target: epic-migrate-kleptocracy-timeline-to-pyrite-managed-kb
  relation: subtask_of
  kb: pyrite
- target: support-string-or-ref-actor-fields-in-cascade-events
  relation: depends_on
  kb: pyrite
kind: feature
status: done
priority: high
effort: M
---

## Problem

Pyrite's backlink system works via wikilinks: when entry A contains `[[entry-b]]`, entry B's backlinks include entry A. However, the Cascade timeline events reference actors as plain strings (e.g., `actors: ["Donald Trump"]`), not wikilinks. Until all actor references are converted to wikilinks (which may never happen fully), the index needs to track string-based actor references so that:

1. An actor entry for "Donald Trump" shows backlinks to all 1,198 events that mention him
2. Search for events by actor name works regardless of reference format
3. The knowledge graph includes actor-event edges from string references

## Context

The kleptocracy timeline has ~7,780 actor references across 4,400+ events. Even after creating actor entries and enabling wikilinks, many events will retain string references during migration. The system should handle both formats transparently.

This is related to "Support string-or-ref actor fields in Cascade events" but focuses specifically on the index/backlink layer rather than the schema layer.

## Scope

- Extend the indexing pipeline to extract string values from configurable fields (e.g., `actors`, `participants`) and create virtual backlink relationships to matching entries
- Match strings to entries via title and aliases (case-insensitive)
- Store these as a distinct link type (e.g., `string_reference`) to distinguish from explicit wikilinks
- Include string-reference backlinks in `pyrite backlinks` output
- Include string-reference edges in knowledge graph API responses
- Reindex incrementally when events or actor entries change

## Acceptance Criteria

- `pyrite backlinks donald-trump --kb=timeline` returns all events where `actors` contains "Donald Trump" (string) or `[[donald-trump]]` (wikilink)
- Knowledge graph shows edges between actor entries and events regardless of reference format
- String references are distinguishable from explicit wikilinks in output (e.g., different link type)
- Index rebuilds correctly when actor aliases change
- Performance: indexing 4,400+ events with 7,780+ actor references completes in under 30 seconds
