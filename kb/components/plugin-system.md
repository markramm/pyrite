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
- `protocol.py` — PyritePlugin Protocol class with 11 methods
- `registry.py` — PluginRegistry: discovery via entry points, registration, and aggregation helpers

## Integration Points
1. **Entry type resolution** — `get_entry_class()` consults registry before GenericEntry fallback
2. **CLI registration** — `cli/__init__.py` adds Typer sub-apps from plugins
3. **MCP tools** — `mcp_server.py` merges plugin tools per tier
4. **Validators** — `schema.py` runs plugin validators (always, even for undeclared types)
5. **Relationship types** — `schema.py` merges plugin relationships into core types
