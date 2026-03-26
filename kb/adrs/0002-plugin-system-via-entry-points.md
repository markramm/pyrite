---
id: adr-0002
type: adr
title: "Plugin System via Python Entry Points"
adr_number: 2
status: accepted
deciders: ["markr"]
date: "2025-10-01"
tags: [architecture, plugins]
---

## Context

Pyrite needs extensibility for different KB use cases (zettelkasten, social, encyclopedia, software). We needed a mechanism for plugins to register entry types, validators, CLI commands, MCP tools, and workflows without modifying core.

## Decision

Use Python `importlib.metadata` entry points under the `pyrite.plugins` group. Each extension declares a plugin class in its `pyproject.toml`. The `PluginRegistry` discovers and loads plugins at startup.

## Consequences

- Extensions are pip-installable packages — standard Python tooling
- Plugins coexist without conflicts — tested with 6 concurrent extensions
- Extensions must be `pip install -e` in the venv for pre-commit hooks to pass

## Addendum (2026-03-26): Protocol Growth

The plugin protocol has grown from 5 integration points and 11 methods to **19 methods** covering:

1. `get_entry_types()` — custom entry type classes
2. `get_type_metadata()` — field definitions, AI instructions, presets
3. `get_collection_types()` — custom collection types
4. `get_mcp_tools(tier)` — per-tier MCP tools
5. `get_cli_commands()` — Typer sub-commands
6. `get_validators()` — entry validation rules
7. `get_relationship_types()` — semantic relationship definitions
8. `get_hooks()` — lifecycle hooks (before/after save/delete)
9. `get_db_columns()` — additional DB columns for entry table
10. `get_db_tables()` — custom DB tables
11. `get_migrations()` — schema migration functions
12. `get_kb_presets()` — KB template presets
13. `get_field_schemas()` — custom field type schemas
14. `get_protocols()` — structural protocol mixins
15. `get_orient_supplement()` — additional orient output
16. `get_rubric_checkers()` — QA rubric evaluation rules
17. `get_workflows()` — workflow definitions
18. `get_kb_types()` — KB type declarations
19. `set_context(ctx)` — receives config, db, and services at startup

Six extensions ship: software-kb, zettelkasten, encyclopedia, social, journalism-investigation, cascade.
