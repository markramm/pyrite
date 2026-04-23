---
id: migrate-cascade-kbs-to-investigation
type: backlog_item
title: "Migrate cascade KBs to investigation kb_type; normalize layout and schema"
kind: feature
status: proposed
priority: high
effort: M
tags: [schema, migration, cascade, journalism-investigation, data-quality]
links:
- target: epic-normalization-and-data-cleanup
  relation: subtask_of
  kb: pyrite
---

## Scope

Migrate these KBs from cascade-plugin-owned to plain investigation KBs:

- `/Users/markr/cascade-kb/cascade-timeline/`
- `/Users/markr/cascade-kb/cascade-research/`
- `/Users/markr/cascade-kb/cascade-solidarity/`

Plus: repo hygiene for cascade-timeline, and a migration CLI for any
out-of-tree cascade KBs.

### kb.yaml migration

For each KB:

- Set `kb_type: investigation`
- Remove the ambiguous `event` type declaration; declare the consolidated
  `timeline_event` type with full field schema copied from JI's
  `InvestigationEventEntry` (or `TimelineEventEntry` after the rename in
  [[rename-investigation-event-to-timeline-event]])
- Declare `required:` lists so [[schema-required-field-validation]]
  catches missing fields
- Update `subdirectory:` declarations per [[clarify-subdirectory-handling]]

### Entry `type:` normalization

- Any entries with `type: event`, `type: political`, `type: legislative`,
  `type: cascade_event`, or missing `type:` that represent timeline
  events → rewrite to `type: timeline_event`
- Any entries with `type: cascade_org` → rewrite to `type: organization`,
  move cascade-specific fields (`tier`, `capture_lanes`) into `metadata:`
  or into optional fields on JI's org schema per [[ji-absorb-cascade-types]]

### cascade-timeline repo hygiene

From the retired `normalize-cascade-timeline-files` item:

1. Remove all `.md.bak` files (15 as of the last audit)
2. Reconcile `cascade-timeline/events/` subdirectory (25 entries) —
   merge into the root with date-prefix filenames (the dominant pattern).
   Update `kb.yaml` to reflect a single root layout.
3. Canonicalize frontmatter field order:
   `type → id → date → title → importance → status → tags → actors →
   sources → body`
4. Check in `scripts/normalize.py` (the one-shot used during today's
   fix) so drift can be caught repeatably.

### Migration CLI for out-of-tree KBs

Add `pyrite kb migrate --from-cascade -k <kb-name>` that:

- Rewrites `type:` frontmatter per the mapping above
- Moves cascade-specific fields into the new schema locations
- Prints a summary of changes (dry-run by default; `--apply` executes)
- Emits a report compatible with `pyrite kb validate` output

This is the path for any user with a cascade-using KB outside the
monorepo (detention-pipeline-research, journalists.pyrite.wiki samples,
community KBs).

## TDD

1. `test_migrate_from_cascade_rewrites_event_types` — fixture KB with
   `type: event` entry, run migrator, assert `type: timeline_event` in
   the rewritten file.
2. `test_migrate_from_cascade_preserves_custom_fields` — `tier: 2` on a
   `cascade_org` survives as `metadata.tier: 2` or as an optional field
   on the new `organization` entry.
3. `test_cascade_timeline_kb_passes_kb_validate` — after migration,
   `pyrite kb validate -k cascade-timeline` exits 0.

## Changes

- `pyrite/cli/kb_commands.py` (or equivalent) — `pyrite kb migrate` command
- `pyrite/services/migration_service.py` (new) — migration logic, type-map, field-remap
- `/Users/markr/cascade-kb/cascade-timeline/kb.yaml` — rewritten
- `/Users/markr/cascade-kb/cascade-timeline/scripts/normalize.py` — checked in
- Same treatment for cascade-research and cascade-solidarity kb.yaml

## Done when

- `pyrite kb validate -k cascade-timeline` exits 0 (no undeclared types,
  no missing required fields, no orphan entries)
- Same for cascade-research and cascade-solidarity
- `capturecascade.org` deploys cleanly from the migrated
  cascade-timeline (no entries dropped from the viewer)
- `pyrite kb migrate --from-cascade` passes tests

## Depends on

[[warn-on-undeclared-entry-type]], [[schema-required-field-validation]],
[[pyrite-kb-validate-command]] (all Phase 0 — used as the
done-criterion), [[ji-absorb-cascade-types]] (types must already be
available in JI)

## Unblocks

[[remove-cascade-plugin]]

## Replaces

Absorbs [[normalize-cascade-timeline-files]] and
[[consolidate-event-type-to-timeline-event]].
