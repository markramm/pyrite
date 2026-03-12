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
status: done
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

## Reference Implementation

`/Users/markr/kleptocracy-timeline/timeline/scripts/maintenance/suggest_actor_aliases.py` (~680 lines, self-contained Python). This is the source to port — read it for algorithm details, edge cases, and the interactive review UX.

## Context

The kleptocracy timeline's `suggest_actor_aliases.py` (~680 lines) is a multi-pass duplicate detection pipeline that scans all actor strings across events and proposes merge groups. It processes ~1,235 unique actors across 4,400+ events, producing an `actor_aliases.json` mapping file (880 lines, ~250 canonical actors with variants).

This is a general-purpose capability that applies to any KB with person, organization, or actor entries — not just timelines.

## Detection Pipeline (6 passes, sequential)

Each pass removes matched actors so later passes don't re-process them:

1. **Case-insensitive exact match** (100% confidence) — "donald trump" ↔ "Donald Trump"
2. **Slug match** (95% confidence) — Normalize to lowercase slugs (strip possessives, punctuation, unicode). Catches "Trump's DOJ" vs "Trumps DOJ"
3. **Prefix stripping** (90% confidence) — Remove U.S./US/United States prefixes, check if stripped version exists separately. "U.S. Department of Justice" ↔ "Department of Justice"
4. **Parenthetical extraction** (90% confidence) — Split "American Legislative Exchange Council (ALEC)" into base name + acronym, merge all variants
5. **Known acronym table** (85% confidence) — Hardcoded dictionary of ~50 government/political acronyms. If "FBI" and "Federal Bureau of Investigation" both appear, group them. Also checks U.S. prefix variants
6. **Fuzzy matching** (variable confidence, threshold 85%) — `difflib.SequenceMatcher` ratio. Groups by first word to avoid O(n²). Only considers actors with 2+ appearances. Confidence = match ratio × 100

### Canonical Name Selection

When merging a group, pick the "best" name using priority:
1. Full name over acronym
2. Without U.S. prefix (unless 80%+ of usage has the prefix)
3. Proper case over lowercase
4. Without parenthetical over with
5. Highest usage count breaks ties

### Review Modes

- **Interactive**: Shows each proposal with confidence score, usage counts, impact. Accept/Reject/Edit/Skip, or set auto-thresholds mid-review (AA90 = auto-accept all ≥90%)
- **Auto**: `--auto=90` accepts everything above threshold without interaction
- **Dry-run**: Shows all proposals, saves nothing
- **Incremental**: Loads existing mappings, excludes already-mapped actors, extends the file

## Scope — What Pyrite Absorbs

The core algorithm ports directly. Key adaptations:

1. **Input source** — Query the Pyrite index for entries and their string fields instead of reading YAML frontmatter directly
2. **Output target** — Update entry `aliases` fields directly, or optionally create/merge actor entries (instead of writing `actor_aliases.json`)
3. **Acronym dictionary** — Configurable per KB (in `kb.yaml` or a separate config file) instead of hardcoded
4. **Generalization** — Works on any string field, not just actors: `pyrite qa suggest-aliases --field=actors --type=cascade_event` or for deduplicating entries of any type

### CLI Command

`pyrite qa suggest-aliases` with flags:
- `--kb` — target KB
- `--type` — entry type to scan (default: all)
- `--field` — field containing strings to deduplicate (default: inferred from type)
- `--auto=N` — auto-accept threshold (0-100)
- `--dry-run` — show proposals without saving
- `--incremental` — skip already-mapped actors

## Acceptance Criteria

- `pyrite qa suggest-aliases --kb=timeline --type=actor` detects duplicate actor entries
- All 6 detection passes implemented with correct confidence levels
- Canonical name selection matches the priority rules above
- Confidence scores are meaningful (90%+ matches are almost always correct)
- Interactive mode allows human review before applying changes
- Auto-accept mode (`--auto=90`) applies high-confidence matches without interaction
- Applied aliases are written to the entry's `aliases` field
- Known acronym dictionary is extensible via kb.yaml or a config file
- Incremental mode avoids re-scanning already-processed entries
- Fuzzy matching groups by first word to avoid O(n²) on large actor sets
