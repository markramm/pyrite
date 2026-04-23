---
id: epic-normalization-and-data-cleanup
type: backlog_item
title: "Epic: KB Normalization and Data Health"
kind: epic
status: proposed
priority: high
effort: L
tags: [data-quality, schema, cascade, journalism-investigation, robustness]
links:
- target: normalize-cascade-timeline-files
  relation: has_subtask
  kb: pyrite
- target: consolidate-event-type-to-timeline-event
  relation: has_subtask
  kb: pyrite
- target: warn-on-undeclared-entry-type
  relation: has_subtask
  kb: pyrite
- target: warn-on-missing-type-fallback
  relation: has_subtask
  kb: pyrite
- target: schema-required-field-validation
  relation: has_subtask
  kb: pyrite
- target: pyrite-kb-validate-command
  relation: has_subtask
  kb: pyrite
- target: clarify-subdirectory-handling
  relation: has_subtask
  kb: pyrite
---

## Problem

Today's cascade-timeline deploy surfaced a pattern of silent data drift and
weak schema enforcement:

- 426 entries had drifted from the canonical type (missing `type:`, or using
  `event` / `political` / `legislative` instead of `timeline_event`). The
  viewer exporter hardcoded `timeline_event`, so all 426 were silently
  dropped from capturecascade.org.
- Pyrite defaults missing-type entries to `note` with no warning. The `note`
  type has no `date` field, so events disappeared from date-sorted views.
- `kb.yaml` in cascade-timeline declared `event` as the canonical type while
  everything else (migration script, exporter, 99% of files) assumed
  `timeline_event` — schema and reality diverged with no mechanism to detect.
- Two separate event types exist across the ecosystem: `timeline_event`
  (cascade plugin) and `investigation_event` (JI plugin). Cascade-timeline
  is an investigation; the split adds ceremony without value.
- `pyrite index build` / `index health` never warned about any of this.

## Goals

1. **Consolidate** on a single canonical event type across cascade and JI:
   `timeline_event`. Rename `investigation_event` → `timeline_event` in the
   JI plugin; cascade continues to use `timeline_event` unchanged.
2. **Enforce** schema at index time so the next drift can't happen silently.
3. **Clean up** cascade-timeline: one consistent layout, one type, predictable
   filenames, no `.md.bak` litter.

## Phases

### Phase 1 — Data cleanup (cascade-timeline)

- [[normalize-cascade-timeline-files]] — repo hygiene: remove `.md.bak`
  files, reconcile the `events/` subdirectory, canonical field order in
  frontmatter, checked-in `scripts/normalize.py` for ongoing drift

### Phase 2 — Type consolidation

- [[consolidate-event-type-to-timeline-event]] — rename
  `investigation_event` → `timeline_event` in the JI plugin; drop the
  parallel type in the cascade plugin; update cascade-timeline kb.yaml to
  declare the consolidated type with its full field schema

### Phase 3 — Pyrite robustness (the part that prevents recurrence)

- [[warn-on-undeclared-entry-type]] — warning at index time when an entry's
  `type` is not declared in `kb.yaml`, surfaced via `pyrite index health`
- [[warn-on-missing-type-fallback]] — warning when `from_frontmatter` falls
  back to `note` because `type:` was absent
- [[schema-required-field-validation]] — on index, verify entries have the
  `required:` fields declared in their type schema
- [[pyrite-kb-validate-command]] — `pyrite kb validate` CLI that runs all
  of the above on demand with JSON output
- [[clarify-subdirectory-handling]] — decide and document whether entries
  must live in their type's declared `subdirectory:`; currently
  `repo.list_files()` recursively globs and silently accepts any layout

## Recommended order

Phase 3 first, then Phase 2, then Phase 1. Rationale: Phase 3's warnings
accurately surface the scope of work for Phases 1 and 2, and prevent the
same bug class from recurring during the migration. Phase 1 is partially
complete (426 entries normalized today) — a repeatable script in cascade-kb
would close the loop.

## Related work already shipped today

- Frontmatter delimiter fix (repository.py): `---` no longer matches inside
  quoted values
- Wikilink extractor fix (index.py): code fences and path-like targets no
  longer count as broken links
- Cascade viewer header labels corrected; viewer `cache: 'no-cache'` for
  fresh data on reseed
- 426 cascade-timeline entries normalized to `type: timeline_event`
