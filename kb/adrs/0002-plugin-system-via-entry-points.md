---
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
- 5 integration points wired: entry type resolution, CLI registration, MCP tools, validators, relationship types
- 11-method protocol (PyritePlugin) covers all extension capabilities
- Plugins coexist without conflicts — tested with 4 concurrent extensions
- Extensions must be `pip install -e` in the venv for pre-commit hooks to pass
