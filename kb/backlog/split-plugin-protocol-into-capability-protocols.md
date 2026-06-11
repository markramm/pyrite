---
id: split-plugin-protocol-into-capability-protocols
title: "Split the 20-method plugin Protocol into narrower capability protocols (or add a Capabilities enum)"
type: backlog_item
tags: [architecture, plugins, protocol, modularity, refactor]
importance: 5
kind: improvement
status: proposed
priority: high
effort: M
rank: 1500
---

## Problem

The plugin Protocol (`pyrite/plugins/protocol.py`) has grown from 5 integration points and 11 methods at ADR-0002's original decision to **20 methods today** (verified at HEAD 2026-06-11: 19 `get_*`/`set_*` defs + `name` attribute). ADR-0002's 2026-03-26 addendum honestly documents this growth, but the underlying interface is past what a single Protocol should carry. Every new integration point takes the path of least resistance: add another `get_X()` to the Protocol.

The 20 methods cluster into **6 implicit subsystems** that the Protocol does not name:

| Subsystem | Methods | What it is |
|---|---|---|
| Type system | `get_entry_types`, `get_type_metadata`, `get_collection_types`, `get_field_schemas`, `get_protocols` | Schema extension |
| Storage extension | `get_db_columns`, `get_db_tables`, `get_migrations`, `get_validators`, `get_hooks` | DB-and-lifecycle |
| Surface registration | `get_cli_commands`, `get_mcp_tools`, `get_kb_presets`, `get_kb_types` | UI/API extension |
| Domain semantics | `get_relationship_types`, `get_workflows`, `get_rubric_checkers` | Vocabulary |
| Runtime context | `set_context`, `get_orient_supplement` | Runtime hooks |
| Identity | `name` attribute | naming |

Concrete costs:

- **Most methods are no-ops in most plugins.** ~12 of 20 return empty in any given extension. Pure cost, no value.
- **Silent-failure surface scales with Protocol size.** The registry's "iterate-all, log-failures-at-debug" loop (already ticketed as `plugin-registry-silent-failures`) compounds with the count of methods it calls. Every method is another silent-skip site.
- **Plugin scope is invisible at the type level.** "Does this plugin extend storage?" is a runtime question (does `get_db_columns` return non-empty?), not a structural one.

## Solution

Pick one of two options:

### Option A — Split into capability protocols (preferred)

Define 5 narrower protocols that plugins opt into:

- `SchemaExtension`: `get_entry_types`, `get_type_metadata`, `get_collection_types`, `get_field_schemas`, `get_protocols`
- `StorageExtension`: `get_db_columns`, `get_db_tables`, `get_migrations`, `get_validators`, `get_hooks`
- `SurfaceExtension`: `get_cli_commands`, `get_mcp_tools`, `get_kb_presets`, `get_kb_types`
- `DomainExtension`: `get_relationship_types`, `get_workflows`, `get_rubric_checkers`
- `ContextAware`: `set_context`, `get_orient_supplement`

The registry dispatches per capability: `for p in registry.with_capability(SchemaExtension): ...`. A plugin that only extends entry types implements only `SchemaExtension`, and the registry never iterates the storage / surface / domain dispatch paths for it. "What does this plugin do?" becomes a structural type-level question.

### Option B — Keep one Protocol, add a Capabilities declaration

Plugins declare a `capabilities: set[Capability]` class attribute. The registry checks the set before calling each method group, skipping the no-op loops. Smaller refactor than Option A but the Protocol surface stays large.

## Acceptance criteria

- Plugin scope (which capabilities a plugin extends) is a structural / declared property, not an implicit runtime one.
- Registry dispatch loops skip capabilities the plugin does not claim — no more iterating all 20 methods for every plugin.
- ADR-0002 gets a follow-up ADR (or a third addendum) documenting the chosen split and the migration path.
- All 6 in-tree extensions migrated to the new shape; tests assert each plugin's declared capabilities match what it actually implements.
- The silent-failure surface in `plugin-registry-silent-failures` reduces by the count of skipped no-op calls.

## Related

- `plugin-registry-silent-failures` — directly compounded by Protocol size; fixing this shrinks the silent-failure surface.
- `implement-extension-type-protocols` — adjacent but distinct work on *entry-type*-level structural protocols (claimable, evidence-linked, etc.). This ticket is about the plugin-class Protocol itself.
- ADR-0002 — needs an addendum or successor ADR if Option A is chosen.
- The modularity report committed alongside this ticket.

## Design questions (yielded from /pyrite-dev cron fire 2026-06-11)

This is a real Option A vs Option B decision that materially changes the migration path. The ticket presents both options but the choice is not locked. A fire that picks this up needs the choice made first; speculating would write a refactor that gets thrown away.

**Recommendation: Option B first, treat Option A as a deprecation-cycle follow-up.**

Rationale:
- Option B is the smaller refactor that delivers most of the value: plugin scope becomes structural via the declared `capabilities` set, registry skips empty dispatch loops, no code moves between files.
- Option A is architecturally cleaner but the migration touches all 6 in-tree extensions plus the registry plus every dispatch loop, and the ADR needs an addendum or successor.
- Landing B first proves the dispatch-skip wins (measurable: hooks fire fewer times, silent-failure log noise drops, plugin-load timing improves) and then A can be done in a follow-up that deprecates Protocol-direct methods in favor of capability-specific base classes without breaking anything.

If the recommendation is accepted (Option B + Option A as follow-up), here is what a fire that picks this up needs locked:

1. **Capability enum naming.** Pyrite-side `Capability` enum vs imported from `typing` (no — those are different). Recommendation: define `pyrite.plugins.capabilities.Capability(StrEnum)` with members `SCHEMA`, `STORAGE`, `SURFACE`, `DOMAIN`, `CONTEXT`. Names mirror the ticket's 5 protocol-subsystem split, future-proofing the eventual move to Option A. Confirm?

2. **Declaration site.** Class attribute `capabilities: ClassVar[set[Capability]] = ...` on each plugin. Default for a plugin missing it: empty set, which means the registry skips ALL dispatch — this is the safe failure mode (a plugin that forgets to declare gets ignored, not silently half-loaded). Alternative: default to all capabilities (back-compat for existing plugins). Recommendation: empty set + migration step that updates every in-tree plugin to declare its real set, fail loudly if a plugin returns non-empty from a method it didn't declare. Confirm?

3. **Method-to-capability map.** Hard-coded in the registry, since the Protocol is shared infrastructure. Recommendation: a module-level constant `_METHOD_CAPABILITIES: dict[str, Capability]` mapping `get_entry_types -> SCHEMA`, `get_db_columns -> STORAGE`, etc. Registry's aggregation helpers check the plugin's declared `capabilities` before calling. Confirm?

4. **What to do with already-implemented methods on plugins that don't declare the capability.** Option B1: log a warning, skip. Option B2: raise PluginError (strict). Option B3: silently fall back to calling them (defeats the optimization). Recommendation: B1 in default mode, B2 in `strict_plugins=True` mode (already a setting). Same shape as the existing strict-discover toggle. Confirm?

5. **Migration of the 6 in-tree extensions.** Each needs `capabilities = {...}` added. They are: `cascade-timeline`, `zettelkasten`, `social`, `encyclopedia`, `software-kb`, `journalism-investigation`. (Plus `cascade-research` if still active.) The migration is mechanical: read each plugin's class, check which `get_*` methods return non-empty, write the set. Worth doing in the same commit so the capability declaration is the source of truth from day one. Confirm?

6. **Tests assert match.** Acceptance criterion 4 in the ticket — "tests assert each plugin's declared capabilities match what it actually implements." Recommendation: add `test_plugin_capabilities_match_implementation` that for each registered plugin, calls every method, checks which return non-empty, and asserts that the declared capability set covers exactly those. The test is the spec. Confirm?

7. **ADR addendum vs successor.** Ticket says "follow-up ADR (or a third addendum)." Recommendation: addendum to ADR-0002 for Option B (it's a refinement of the same decision); reserve a successor ADR for Option A when that lands later (it's a structural change to the contract). Confirm?

If all 7 recommendations are accepted as-written, the next fire can go straight to RED tests + implementation. Estimate: ~2 fires for the Capability enum + registry dispatch skipping + tests, 1 fire per extension to migrate (so 6 fires for the in-tree set), 1 fire for the ADR addendum. Total ~9 fires, or one focused session.

If Option A is chosen instead, estimate roughly doubles since each extension's class hierarchy changes.
