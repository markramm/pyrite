---
id: cli-system
type: component
title: "CLI System"
kind: cli
path: "pyrite/cli/"
owner: "markr"
dependencies: ["typer", "rich", "pyrite.plugins"]
tags: [core, cli]
---

Typer-based CLI with a root app and eleven domain-specific sub-apps. Commands share infrastructure through context managers that construct PyriteConfig, PyriteDB, and services with guaranteed cleanup. Plugin-provided CLI commands are dynamically registered at startup.

## Architecture

- Root `typer.Typer` app with `add_typer()` for each sub-app
- `context.py` provides `cli_context()`, `cli_registry_context()`, `cli_db_context()`
- Rich tables and console for human-readable output
- Plugin commands discovered via `PluginRegistry.get_all_cli_commands()`

## Sub-Apps

- `kb` — list, add, remove, discover, validate knowledge bases
- `index` — build, sync, stats, embed, health
- `search` — full-text and semantic search
- `qa` — rubric-based quality evaluation
- `repo` — git repository subscribe, fork, sync
- `collections` — collection management
- `links` — wikilink graph operations
- `schema` — schema inspection and migration
- `task` — task management
- `db` — database migration and inspection
- `export` — export entries to various formats
- `extension` — install, list, enable/disable extensions

## Related

- [[plugin-system]] — dynamic command registration
- [[config-system]] — shared configuration
