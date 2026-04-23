---
id: ji-absorb-cascade-types
type: backlog_item
title: "Move cascade entry types, relationships, validators, and hooks into JI plugin"
kind: feature
status: proposed
priority: high
effort: M
tags: [schema, journalism-investigation, cascade, deprecation]
links:
- target: epic-normalization-and-data-cleanup
  relation: subtask_of
  kb: pyrite
---

## Scope

Move these from `extensions/cascade/` into
`extensions/journalism-investigation/`:

### Entry types (7 kept, 2 dropped)

Keep and move. Class names stay un-prefixed (decision resolved in epic:
no `Ji…` prefix — JI is the canonical home, the package path
disambiguates):

- `actor` (`ActorEntry`) — extends `PersonEntry`, adds `tier`, `era`,
  `capture_lanes`, `chapters`
- `theme` (`ThemeEntry`) — extends `TopicEntry`
- `victim` (`VictimEntry`) — extends `Entry` + `Locatable`
- `statistic` (`StatisticEntry`)
- `mechanism` (`MechanismEntry`)
- `scene` (`SceneEntry`)
- `solidarity_event` (`SolidarityEventEntry`) — extends `EventEntry`

The cascade plugin's `TimelineEventEntry` already inherits from JI's
`InvestigationEventEntry`. Once cascade is gone, JI's class *is* the
canonical timeline event. The type-string rename lands in a later ticket
([[rename-investigation-event-to-timeline-event]]).

Drop (redundant):

- `cascade_org` — just `OrganizationEntry` with `tier` + `capture_lanes`.
  Collapse those fields into the `metadata` bag on standard
  `organization` entries, or add them as optional fields on JI's
  existing org type.
- `cascade_event` — thin wrapper over `EventEntry`, unused (all real
  events are `timeline_event`). Delete; migrate any existing
  entries to `timeline_event` during Phase 2.

### Relationship types (all 9 + inverses)

Move these from `CascadePlugin.get_relationship_types()` to
`JournalismInvestigationPlugin.get_relationship_types()`:

`member_of` / `has_member`, `investigated` / `investigated_by`,
`funded_by` / `funds`, `capture_mechanism` / `enabled_capture`,
`built_on` / `enabled`, `responded_to` / `provoked_response`,
`actor_reference` / `has_actor`.

Check for collisions with JI's existing relationship types before
merging — `funded_by` / `funds` are the likely candidates.

### Validators

Move `_validate_cascade_entry` from
`extensions/cascade/src/pyrite_cascade/plugin.py` to JI's validators
module. Rename to reflect the new home (e.g., `_validate_actor_entry`,
`_validate_solidarity_event`), or fold the checks into existing JI
validators where the types already overlap.

### Hooks

Move `resolve_actor_links` (before_save) and `_on_actor_saved`
(after_save) from `extensions/cascade/src/pyrite_cascade/hooks.py` to
JI's hooks module. Also move the actor lookup cache
(`_actor_cache`, `invalidate_actor_cache`) and alias-loading helper.

The hook currently triggers on `timeline_event`, `solidarity_event`,
`scene` — keep that trigger set.

## TDD

Failing tests first, in JI's test suite:

1. `test_ji_provides_actor_entry_type` — `JournalismInvestigationPlugin().get_entry_types()["actor"] is ActorEntry`
2. `test_ji_provides_cascade_relationship_types` — `"capture_mechanism" in JournalismInvestigationPlugin().get_relationship_types()`
3. `test_resolve_actor_links_runs_on_timeline_event` — save a
   `timeline_event` with `actors: ["Donald Trump"]` in a KB that has a
   matching actor entry, assert `actor_reference` link is added

## Changes

- `extensions/journalism-investigation/src/pyrite_journalism_investigation/entry_types.py` — import or move cascade classes
- `extensions/journalism-investigation/src/pyrite_journalism_investigation/plugin.py` — register new types, relationships, hooks, validators
- `extensions/journalism-investigation/src/pyrite_journalism_investigation/validators.py` — add cascade validators
- `extensions/journalism-investigation/src/pyrite_journalism_investigation/hooks.py` — add actor-resolution hooks
- `extensions/cascade/src/pyrite_cascade/plugin.py` — remove moved bits, keep the plugin as a thin shim importing from JI for one release (see [[remove-cascade-plugin]])

## Done when

- All 7 kept types, 9 relationships, both hooks, and validator land in
  JI
- JI tests covering the moved surface pass
- Cascade plugin still loads and exposes the same types via
  re-export shim (full removal in Phase 3)
- A migration plan for `cascade_org` and `cascade_event` entries is
  written into [[migrate-cascade-kbs-to-investigation]]

## Depends on

Phase 0 complete ([[warn-on-undeclared-entry-type]],
[[schema-required-field-validation]]) so any during-migration drift
surfaces in `index health`.

## Unblocks

[[ji-absorb-cascade-cli]], [[ji-absorb-cascade-mcp]],
[[migrate-cascade-kbs-to-investigation]]
