---
type: design_doc
title: "Plugin Protocol Design"
status: implemented
author: "markr"
date: "2025-10-01"
reviewers: []
tags: [architecture, plugins]
---

## Overview

The PyritePlugin protocol defines the contract between pyrite core and extensions. It uses Python's Protocol (structural subtyping) so plugins don't need to inherit from a base class.

## Protocol Methods (15 + `name` attribute)

### Original 7
1. `get_entry_types() -> dict[str, type]` — maps type name to Entry subclass
2. `get_kb_types() -> list[str]` — KB type identifiers this plugin handles
3. `get_cli_commands() -> list[tuple[str, Any]]` — (name, typer_app) pairs
4. `get_mcp_tools(tier: str) -> dict[str, dict]` — MCP tools with handler callbacks
5. `get_db_columns() -> list[dict]` — additional columns for core entry table
6. `get_relationship_types() -> dict[str, dict]` — with inverse mappings
7. `get_validators() -> list[Callable]` — signature: (entry_type, data, context) -> list[dict]

### Added in Wave 5C-6
8. `get_hooks() -> dict[str, list[Callable]]` — lifecycle hooks (before_save, after_save, etc.)
9. `get_kb_presets() -> dict[str, dict]` — preset KB configurations
10. `get_workflows() -> dict[str, dict]` — state machine definitions
11. `get_db_tables() -> list[dict]` — custom DB table definitions

### Added in Wave 7-12
12. `get_field_schemas() -> dict[str, dict[str, dict]]` — rich field schema definitions (FieldSchema format) per type
13. `get_type_metadata() -> dict[str, dict]` — AI instructions, field descriptions, display hints per type
14. `get_collection_types() -> dict[str, dict]` — custom collection type definitions
15. `set_context(ctx: PluginContext) -> None` — receive DI container with DB, config, services

### Attribute
- `name: str` — plugin identifier string

## Design Decisions
- Structural typing (Protocol) over inheritance — extensions don't need to import core
- All methods optional via default implementations — start minimal, add capabilities
- Validators changed from `(type, data)` to `(type, data, context)` with backwards-compatible fallback
- CLI imported lazily to handle missing typer gracefully
