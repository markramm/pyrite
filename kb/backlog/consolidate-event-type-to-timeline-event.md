---
id: consolidate-event-type-to-timeline-event
type: backlog_item
title: "Consolidate investigation_event and timeline_event into a single type"
kind: feature
status: superseded
priority: high
effort: M
tags: [schema, journalism-investigation, cascade, migration, superseded]
links:
- target: rename-investigation-event-to-timeline-event
  relation: superseded_by
  kb: pyrite
- target: migrate-cascade-kbs-to-investigation
  relation: superseded_by
  kb: pyrite
---

**Superseded.** Split into two tickets after decision to deprecate the
cascade plugin entirely: [[rename-investigation-event-to-timeline-event]]
handles the JI-internal rename once cascade is gone, and
[[migrate-cascade-kbs-to-investigation]] handles data migration.

---

Original scope, preserved for reference:

Cascade-timeline is an investigation. The parallel `timeline_event`
(cascade plugin) and `investigation_event` (JI plugin) types add ceremony
without value. Consolidate on `timeline_event`.

## Changes

### Journalism-investigation plugin
- Rename `investigation_event` → `timeline_event` in
  `extensions/journalism-investigation/src/pyrite_journalism_investigation/entry_types.py`
- Update all internal references (validators, tests, presets)
- Keep `InvestigationEventEntry` as the Python class name, but map it to
  the new `timeline_event` type string
- Add a one-shot migration for any existing `investigation_event` entries
  in the wild (detention-pipeline-research, future investigations)

### Cascade plugin
- Remove the now-duplicate `TimelineEventEntry` local class if it's
  separate from JI's; otherwise make it extend the JI one
- Keep `extensions/cascade/src/pyrite_cascade/static_export.py` querying
  `timeline_event` (already does)

### cascade-timeline kb.yaml
- Declare `timeline_event` (not `event`) as the type
- Copy the full field schema from JI's InvestigationEventEntry so
  validation / required-field checks work

### Downstream
- Any extension or consumer searching for `investigation_event` (e.g.
  detention-pipeline-research, journalists.pyrite.wiki sample KBs) needs
  updating via migration

## TDD approach

Test first: `test_timeline_event_type_string_consistent_across_plugins`
that asserts both cascade's TimelineEventEntry and JI's
InvestigationEventEntry produce `entry_type == "timeline_event"`.

Blocks: Phase 1 cleanup (want these to land after type consolidation so
scripts target the final name).
Blocked by: nothing.
