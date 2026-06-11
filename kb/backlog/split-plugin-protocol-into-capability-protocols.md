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

## Design (LOCKED 2026-06-11 by Mark)

**Option B chosen.** Option A (split into 5 capability protocols) is reserved as a deprecation-cycle follow-up once B proves the dispatch-skip wins.

### Capability enum

```python
# pyrite/plugins/capabilities.py
from enum import StrEnum

class Capability(StrEnum):
    SCHEMA = "schema"        # entry types, type metadata, collection types,
                             # field schemas, protocols
    STORAGE = "storage"      # db columns, db tables, migrations, validators,
                             # hooks
    SURFACE = "surface"      # CLI commands, MCP tools, KB presets, KB types
    DOMAIN = "domain"        # relationship types, workflows, rubric checkers
    CONTEXT = "context"      # set_context, get_orient_supplement
```

The 5 members mirror the 5-subsystem split documented above, so an eventual move to Option A is mechanical: each Capability becomes its own Protocol with the same name.

### Plugin declaration

Plugins declare a `capabilities` class attribute:

```python
class MyPlugin:
    name = "my-plugin"
    capabilities: ClassVar[set[Capability]] = {Capability.SCHEMA, Capability.SURFACE}

    def get_entry_types(self) -> dict[str, type]:
        return {"my_type": MyTypeEntry}

    def get_cli_commands(self) -> list[tuple[str, Any]]:
        return [...]
```

**Default for missing declaration: empty set.** A plugin without `capabilities` is treated as having ZERO declared capabilities — the registry skips ALL its dispatch loops. This is the safe failure mode: a plugin that forgets to declare gets ignored entirely rather than silently half-loaded.

### Migration

All 6 in-tree extensions get a `capabilities` set in the SAME commit that lands the registry change. No phased rollout. Migration is mechanical: read each plugin's class, check which `get_*` methods return non-empty, write the set. Extensions:

- `zettelkasten`
- `social`
- `encyclopedia`
- `software-kb`
- `journalism-investigation`
- (plus `cascade` if still active — confirm at fire time)

### Method-to-capability map

Hard-coded in the registry as a module-level constant:

```python
# pyrite/plugins/registry.py
_METHOD_CAPABILITIES: dict[str, Capability] = {
    "get_entry_types": Capability.SCHEMA,
    "get_type_metadata": Capability.SCHEMA,
    "get_collection_types": Capability.SCHEMA,
    "get_field_schemas": Capability.SCHEMA,
    "get_protocols": Capability.SCHEMA,
    "get_db_columns": Capability.STORAGE,
    "get_db_tables": Capability.STORAGE,
    "get_migrations": Capability.STORAGE,
    "get_validators": Capability.STORAGE,
    "get_hooks": Capability.STORAGE,
    "get_cli_commands": Capability.SURFACE,
    "get_mcp_tools": Capability.SURFACE,
    "get_kb_presets": Capability.SURFACE,
    "get_kb_types": Capability.SURFACE,
    "get_relationship_types": Capability.DOMAIN,
    "get_workflows": Capability.DOMAIN,
    "get_rubric_checkers": Capability.DOMAIN,
    "set_context": Capability.CONTEXT,
    "get_orient_supplement": Capability.CONTEXT,
}
```

The registry's aggregation helpers (`_aggregate_dict`, `_aggregate_list`, `_aggregate_dict_of_lists`) check `_METHOD_CAPABILITIES[method_name] in plugin.capabilities` before calling.

### Strict-mode behavior

When a plugin returns non-empty from a method whose capability it did NOT declare:

- **Default (warn-and-skip):** log a WARNING with plugin name + method name + declared capabilities; treat the return value as empty for aggregation purposes.
- **`strict_plugins=True`:** raise `PluginError` immediately.

Mirrors the existing `strict_plugins` discover-toggle. Same shape, same UX.

### Test contract

New test in `tests/test_plugin_integration.py`:

```python
def test_plugin_capabilities_match_implementation():
    """For every registered plugin, the declared `capabilities` set
    must cover exactly the methods that return non-empty data.
    Catches drift between the declaration and the implementation."""
```

For each registered plugin, calls every method in `_METHOD_CAPABILITIES`, checks which return non-empty, derives the implied capability set from those, and asserts it equals (or is a subset of) the declared `capabilities`. The test is the spec.

### ADR

Land an **addendum** to ADR-0002 documenting:
- The Capability enum + declaration site
- The dispatch-skip behavior
- The empty-set default and the migration step
- The reservation of a successor ADR for Option A

A successor ADR (separate file) is reserved for whenever Option A lands, since that's a structural change to the contract (Protocol → capability-specific base classes).

## Acceptance criteria

- `pyrite.plugins.capabilities.Capability` StrEnum with 5 members (SCHEMA, STORAGE, SURFACE, DOMAIN, CONTEXT) exists.
- Every in-tree plugin (6 extensions) declares a `capabilities: ClassVar[set[Capability]]` set in the same commit.
- Registry aggregation helpers (`_aggregate_dict`, `_aggregate_list`, `_aggregate_dict_of_lists`) consult `_METHOD_CAPABILITIES` and `plugin.capabilities` before calling — skipping methods whose capability is not declared.
- A plugin returning non-empty from an undeclared-capability method triggers a WARNING by default; raises `PluginError` under `strict_plugins=True`.
- `test_plugin_capabilities_match_implementation` passes for every in-tree plugin.
- ADR-0002 addendum filed documenting the Capability enum + dispatch-skip behavior + empty-set default.
- `plugin-registry-silent-failures` follow-up `admin-plugin-info-endpoint-should-expose-has-errors-error-list-when-partial-aggregation-occurred` reduces in surface — the silent-failure log noise shrinks by the count of methods skipped per plugin.

## Implementation arc

Estimated ~3 fires:
1. Capability enum + registry dispatch-skip + RED test for declaration-mismatch
2. Migrate all 6 in-tree extensions in same commit (mechanical: walk each plugin, declare its real capabilities, run the new test)
3. ADR-0002 addendum + component-doc update + commit message that closes the ticket

## Related

- `plugin-registry-silent-failures` (closed in commit a7d347e) — directly compounded by Protocol size; this ticket shrinks the silent-failure surface measurably.
- `admin-plugin-info-endpoint-should-expose-has-errors-error-list-when-partial-aggregation-occurred` — follow-up from the silent-failures lock; partial aggregation has fewer false positives once dispatch-skip lands.
- `implement-extension-type-protocols` — adjacent but distinct work on *entry-type*-level structural protocols (claimable, evidence-linked, etc.). This ticket is about the plugin-class Protocol itself.
- ADR-0002 — gets an addendum for B; successor ADR reserved for A.
- The modularity report committed alongside this ticket.
