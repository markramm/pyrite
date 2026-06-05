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

The plugin Protocol (`pyrite/plugins/protocol.py`) has grown from 5 integration
points and 11 methods at ADR-0002's original decision to **20 methods today**.
ADR-0002's 2026-03-26 addendum honestly documents this growth, but the
underlying interface is past what a single Protocol should carry. Every new
integration point takes the path of least resistance: add another `get_X()` to
the Protocol.

The 20 methods cluster into **6 implicit subsystems** that the Protocol does
not name:

| Subsystem | Methods | What it is |
|---|---|---|
| Type system | `get_entry_types`, `get_type_metadata`, `get_collection_types`, `get_field_schemas`, `get_protocols` | Schema extension |
| Storage extension | `get_db_columns`, `get_db_tables`, `get_migrations`, `get_validators`, `get_hooks` | DB-and-lifecycle |
| Surface registration | `get_cli_commands`, `get_mcp_tools`, `get_kb_presets`, `get_kb_types` | UI/API extension |
| Domain semantics | `get_relationship_types`, `get_workflows`, `get_rubric_checkers` | Vocabulary |
| Runtime context | `set_context`, `get_orient_supplement` | Runtime hooks |
| Identity | `name` attribute | naming |

Concrete costs:

- **Most methods are no-ops in most plugins.** ~12 of 20 return empty in any
  given extension. Pure cost, no value.
- **Silent-failure surface scales with Protocol size.** The registry's
  "iterate-all, log-failures-at-debug" loop (already ticketed as
  `plugin-registry-silent-failures`) compounds with the count of methods it
  calls. Every method is another silent-skip site.
- **Plugin scope is invisible at the type level.** "Does this plugin extend
  storage?" is a runtime question (does `get_db_columns` return non-empty?),
  not a structural one.

## Solution

Pick one of two options:

### Option A — Split into capability protocols (preferred)

Define 5 narrower protocols that plugins opt into:

- `SchemaExtension`: `get_entry_types`, `get_type_metadata`, `get_collection_types`,
  `get_field_schemas`, `get_protocols`
- `StorageExtension`: `get_db_columns`, `get_db_tables`, `get_migrations`,
  `get_validators`, `get_hooks`
- `SurfaceExtension`: `get_cli_commands`, `get_mcp_tools`, `get_kb_presets`,
  `get_kb_types`
- `DomainExtension`: `get_relationship_types`, `get_workflows`, `get_rubric_checkers`
- `ContextAware`: `set_context`, `get_orient_supplement`

The registry dispatches per capability: `for p in registry.with_capability(SchemaExtension): ...`
A plugin that only extends entry types implements only `SchemaExtension`, and
the registry never iterates the storage / surface / domain dispatch paths for
it. "What does this plugin do?" becomes a structural type-level question.

### Option B — Keep one Protocol, add a Capabilities declaration

Plugins declare a `capabilities: set[Capability]` class attribute. The registry
checks the set before calling each method group, skipping the no-op loops.
Smaller refactor than Option A but the Protocol surface stays large.

## Acceptance criteria

- Plugin scope (which capabilities a plugin extends) is a structural / declared
  property, not an implicit runtime one.
- Registry dispatch loops skip capabilities the plugin does not claim — no more
  iterating all 20 methods for every plugin.
- ADR-0002 gets a follow-up ADR (or a third addendum) documenting the chosen
  split and the migration path.
- All 6 in-tree extensions migrated to the new shape; tests assert each
  plugin's declared capabilities match what it actually implements.
- The silent-failure surface in `plugin-registry-silent-failures` reduces by
  the count of skipped no-op calls.

## Related

- [[plugin-registry-silent-failures]] — directly compounded by Protocol size;
  fixing this shrinks the silent-failure surface.
- [[implement-extension-type-protocols]] — adjacent but distinct work on
  *entry-type*-level structural protocols (claimable, evidence-linked, etc.).
  This ticket is about the plugin-class Protocol itself.
- ADR-0002 — needs an addendum or successor ADR if Option A is chosen.
- The modularity report committed alongside this ticket.
