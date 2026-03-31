---
id: plugin-system
type: component
title: "Plugin System"
kind: module
path: "pyrite/plugins/"
owner: "markr"
dependencies: ["pyrite.models", "pyrite.schema"]
tags: [core, extensibility]
---

Lazy-loaded plugin system using Python entry points for discovery and a structural protocol for capabilities. Plugins are ordinary classes implementing any subset of 20 optional methods — no base class required. The registry aggregates contributions across all loaded plugins with collision detection.

## Architecture

- `protocol.py` — `PyritePlugin` @runtime_checkable protocol (20 methods)
- `registry.py` — `PluginRegistry` singleton, lazy discovery via `importlib.metadata.entry_points(group="pyrite.plugins")`
- `context.py` — `PluginContext` dataclass injected into plugins via `set_context()`

## Plugin Lifecycle

1. `get_registry()` triggers lazy discovery of entry points
2. Each plugin class is instantiated and `set_context()` injects shared config/db
3. Registry exposes `get_all_*()` aggregation methods per capability axis
4. Dict capabilities warn on key collisions, list capabilities extend, dict-of-list merge by key
5. `run_hooks_for_kb()` filters hooks by KB type for domain-scoped plugins

## Capabilities

Entry types, CLI commands, MCP tools, DB schema (columns + tables), relationship types, workflows, hooks (before/after save/delete/index), KB presets, field schemas, type metadata, collection types, validators, migrations, protocols, orient supplements, rubric checkers

## Related

- [[pyrite-plugin-protocol]] — the protocol definition
- [[mcp-server]] — MCP tool registration from plugins
- [[software-kb-extension]] — canonical plugin implementation
