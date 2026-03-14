---
id: ji-cross-kb-entity-dedup
title: Cross-KB entity deduplication and linking
type: backlog_item
tags:
- journalism
- investigation
- entities
- cross-kb
- dedup
links:
- target: epic-cross-kb-investigation-search
  relation: subtask_of
  kb: pyrite
- target: ji-unified-cross-kb-search
  relation: depends_on
  kb: pyrite
- target: actor-alias-suggestion-and-fuzzy-matching-tool
  relation: depends_on
  kb: pyrite
kind: feature
status: done
priority: high
effort: M
---

## Problem

The same person or organization appears in multiple investigation KBs. "Vladimir Putin" in the kleptocracy timeline is the same entity as "Vladimir Putin" in a separate oligarch investigation KB. Currently there's no way to detect this or link the entries across KBs.

## Scope

- Cross-KB entity matching using the alias fuzzy matching pipeline (reuse from actor-alias-suggestion tool)
- Match by: title, aliases, key identifiers (jurisdiction, org_type)
- Create cross-KB links: `same_as` relationship type linking entries across KBs
- CLI: `pyrite investigation find-duplicates --across-kbs`
- MCP tool: `investigation_find_duplicates` — scan for cross-KB matches
- Review mode: show matches with confidence scores, accept/reject
- Accepted matches create `same_as` links visible in entity profile views

## Acceptance Criteria

- Cross-KB matching detects same entities across 2+ KBs
- Fuzzy matching reuses the 6-pass alias detection pipeline
- `same_as` links traversable in both directions
- Entity profile view shows cross-KB appearances
- No data modification in source KBs — links are additive only
