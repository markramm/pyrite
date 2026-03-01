---
type: component
title: "Plugin System"
kind: module
path: "pyrite/plugins/"
owner: "markr"
dependencies: ["pyrite.models", "pyrite.schema"]
tags: [core, extensibility]
---

The plugin system enables extensions to add entry types, CLI commands, MCP tools, validators, workflows, relationship types, DB tables, hooks, and KB presets.

## Key Files
- `protocol.py` — PyritePlugin Protocol class with 16 methods + `name` attribute
- `registry.py` — PluginRegistry: discovery via entry points, registration, and aggregation helpers
- `context.py` — PluginContext: DI container injected via `set_context()` (DB, config, services)

## Protocol Methods (16)

| # | Method | Purpose |
|---|--------|---------|
| 1 | `get_entry_types()` | Map type name → Entry subclass |
| 2 | `get_kb_types()` | KB type identifiers this plugin handles |
| 3 | `get_cli_commands()` | (name, typer_app) pairs for CLI registration |
| 4 | `get_mcp_tools(tier)` | MCP tools with handler callbacks per tier |
| 5 | `get_db_columns()` | Additional columns for core entry table |
| 6 | `get_relationship_types()` | Custom relationship types with inverses |
| 7 | `get_workflows()` | State machine definitions |
| 8 | `get_db_tables()` | Custom DB table definitions |
| 9 | `get_hooks()` | Lifecycle hooks (before_save, after_save, etc.) |
| 10 | `get_kb_presets()` | Preset KB configurations for `pyrite init --preset` |
| 11 | `get_validators()` | Validation functions: (entry_type, data, context) → errors |
| 12 | `get_field_schemas()` | Rich field schema definitions (FieldSchema format) |
| 13 | `get_type_metadata()` | AI instructions, field descriptions, display hints per type |
| 14 | `get_collection_types()` | Custom collection type definitions |
| 15 | `set_context(ctx)` | Receive PluginContext with DB, config, services (DI) |
| 16 | `get_migrations()` | Schema migration functions for entry type version upgrades |

All methods are optional — implement only what you need.

## Integration Points
1. **Entry type resolution** — `get_entry_class()` consults registry before GenericEntry fallback
2. **CLI registration** — `cli/__init__.py` adds Typer sub-apps from plugins
3. **MCP tools** — `mcp_server.py` merges plugin tools per tier
4. **Validators** — `schema.py` runs plugin validators (always, even for undeclared types)
5. **Relationship types** — `schema.py` merges plugin relationships into core types
6. **DI injection** — `set_context()` called after discovery to inject PluginContext (DB, config, KB type)
7. **Schema integration** — `get_field_schemas()` and `get_type_metadata()` merged into schema resolution
