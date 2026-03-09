---
id: actor-extraction-and-migration-tool-for-cascade-timelines
title: Actor extraction and migration tool for Cascade timelines
type: backlog_item
tags:
- cascade
- actors
- migration
- cli
links:
- target: epic-migrate-kleptocracy-timeline-to-pyrite-managed-kb
  relation: subtask_of
  kb: pyrite
- target: support-string-or-ref-actor-fields-in-cascade-events
  relation: depends_on
  kb: pyrite
- target: actor-alias-suggestion-and-fuzzy-matching-tool
  relation: depends_on
  kb: pyrite
kind: feature
status: accepted
priority: high
effort: L
---

## Problem

When migrating an existing timeline (like the kleptocracy timeline's 4,400+ events) into Pyrite with the Cascade plugin, actor names exist as plain strings in event files. These need to be extracted into proper actor KB entries, with aliases populated, and event files optionally rewritten to use wikilinks instead of strings.

No automated tooling exists for this migration path.

## Reference Files

- Alias mapping: `/Users/markr/kleptocracy-timeline/timeline/data/actor_aliases.json` (880 lines, ~250 canonical actors). Format: `{"canonical name": ["alias1", "alias2"]}` sorted alphabetically.
- Alias suggestion tool: `/Users/markr/kleptocracy-timeline/timeline/scripts/maintenance/suggest_actor_aliases.py` (produces the alias file)

## Context

The kleptocracy timeline has ~1,235 unique canonical actor names (after alias normalization) appearing ~7,780 times across 4,400+ events. Actors range from individuals (Donald Trump, Pete Hegseth) to organizations (FBI, Heritage Foundation) to informal groups (Congressional Oversight). Many actors appear with multiple name variants that are mapped via an 880-line actor_aliases.json file.

The migration needs to:
1. Scan all events, collect unique actor strings
2. Group variants using the existing alias mappings
3. Create actor entries for each canonical actor (with aliases populated)
4. Optionally classify actors (person vs organization vs group)
5. Optionally rewrite event actor fields from strings to wikilinks
6. Preserve all existing event content (non-destructive)

## Scope

- Create a `pyrite cascade extract-actors` CLI command (or similar)
- Scan events of type `cascade_event` (or configurable types) for actor string fields
- Group actor names using alias mappings (from entry aliases or an external alias file)
- Generate actor entries with: title, type (person/organization), aliases, tags (derived from event tags), importance (based on appearance count)
- Support dry-run mode: show what would be created without creating
- Support incremental mode: only process actors not already in KB
- Optionally rewrite event files to replace string actors with wikilinks
- Import existing alias files (e.g., actor_aliases.json) to bootstrap aliases
- Report: actors created, events updated, unresolved variants

## Acceptance Criteria

- `pyrite cascade extract-actors --kb=timeline --dry-run` reports all unique actors and proposed entries
- `pyrite cascade extract-actors --kb=timeline` creates actor entries with proper aliases
- `pyrite cascade extract-actors --kb=timeline --rewrite` also updates event files to use wikilinks
- Incremental mode skips actors that already have KB entries
- Import of external alias files works: `--alias-file=actor_aliases.json`
- Actor entries include computed importance based on event appearance frequency
- No data loss: event files are only modified in the actors field, all other content preserved
