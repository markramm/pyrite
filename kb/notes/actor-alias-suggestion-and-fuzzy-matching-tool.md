---
id: actor-alias-suggestion-and-fuzzy-matching-tool
title: Actor alias suggestion and fuzzy matching tool
type: backlog_item
tags:
- cascade
- actors
- aliases
- qa
- normalization
links:
- target: epic-migrate-kleptocracy-timeline-to-pyrite-managed-kb
  relation: subtask_of
  kb: pyrite
kind: feature
status: accepted
priority: high
effort: L
---

## Problem

The kleptocracy timeline project built a sophisticated actor alias detection system (`suggest_actor_aliases.py`) that uses fuzzy matching, Levenshtein distance, and a known acronym dictionary to detect duplicate actor names and suggest canonical mappings. This infrastructure exists only in the kleptocracy timeline repo and needs to be absorbed into Pyrite as a core capability.

Currently, Pyrite entries have an `aliases` field, and the wikilink service resolves links by checking aliases. But there is no tooling to:

1. Detect potential duplicates across entries (e.g., "FBI" and "Federal Bureau of Investigation" are the same entity)
2. Suggest alias mappings automatically using fuzzy matching
3. Maintain a known acronym dictionary (50+ acronyms like FBI, CIA, NSA, DOJ, DOGE, ACLU, etc.)
4. Interactively review and approve alias suggestions

## Context

The kleptocracy timeline's `suggest_actor_aliases.py` uses multiple detection strategies:
- Levenshtein distance for fuzzy name matching
- Acronym expansion (maps "FBI" → "Federal Bureau of Investigation")
- 80+ known acronym mappings
- Interactive approval workflow with auto-accept at configurable confidence thresholds
- Outputs an `actor_aliases.json` mapping file (currently 880 lines, ~250 canonical actors with variants)

This is a general-purpose capability that applies to any KB with person, organization, or actor entries — not just timelines.

## Scope

- Create a `pyrite qa suggest-aliases` (or similar) CLI command that scans entries of specified types and detects potential duplicates
- Implement fuzzy matching strategies: Levenshtein distance, acronym expansion, substring matching, parenthetical extraction (e.g., "American Legislative Exchange Council (ALEC)" → alias "ALEC")
- Ship a default known-acronym dictionary for common political/government entities, extensible per KB
- Support interactive review mode (show match, confidence score, accept/reject/skip)
- Support auto-accept mode at configurable confidence threshold (e.g., `--auto=90`)
- Apply approved aliases: update target entries' `aliases` field
- Optionally merge duplicate entries (with backlink preservation)
- Support incremental mode: only scan new/changed entries since last run

## Acceptance Criteria

- `pyrite qa suggest-aliases --kb=timeline --type=actor` detects duplicate actor entries
- Confidence scores are meaningful (90%+ matches are almost always correct)
- Interactive mode allows human review before applying changes
- Auto-accept mode (`--auto=90`) applies high-confidence matches without interaction
- Applied aliases are written to the entry's `aliases` field
- Known acronym dictionary is extensible via kb.yaml or a config file
- Incremental mode avoids re-scanning already-processed entries
