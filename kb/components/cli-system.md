---
type: component
title: "CLI System"
kind: cli
path: "pyrite/cli/"
owner: "markr"
dependencies: ["typer", "rich", "pyrite.plugins"]
tags: [core, cli]
---

Pyrite provides three CLI entry points with different permission levels:

## Entry Points
- `pyrite` — Write-tier (Typer-based, full CRUD operations)
- `pyrite-read` — Read-only (safe for agents): `get`, `list`, `search`, `timeline`, `tags`, `backlinks`, `config`
- `pyrite-admin` — Admin (KB management, indexing, repos, auth)

## Typer App (pyrite/cli/__init__.py)
The Typer-based app provides the richest interface:
- `kb` subcommand (`kb_commands.py`): list, add, remove, discover, validate, create (with `--ephemeral --ttl`), gc
- `index` subcommand (`index_commands.py`): build, sync, stats, embed, health
- `repo` subcommand (`repo_commands.py`): add, remove, subscribe, fork, sync
- `search` subcommand (`search_commands.py`): keyword, semantic, hybrid modes
- `auth` subcommand: github-login, whoami, status
- `serve` — Launch FastAPI + SvelteKit web server
- Plugin sub-apps registered dynamically (e.g., `sw`, `zettel`, `wiki`)

## KB Management Commands

```bash
pyrite kb list                          # List registered KBs
pyrite kb create --name foo --path /p   # Create permanent KB
pyrite kb create --ephemeral --ttl 3600 # Create temporary KB with TTL
pyrite kb gc                            # Garbage-collect expired ephemeral KBs
pyrite kb add /path/to/kb               # Register existing KB
pyrite kb remove <name>                 # Unregister KB
```

## Plugin CLI Integration

Plugins register Typer sub-apps via `get_cli_commands()`. The software-kb extension adds `sw` (components, adrs, backlog, standards). The zettelkasten extension adds `zettel` for slip-box operations.

## Related

- [Config System](config-system.md) — KB configuration and discovery
- [KB Service](kb-service.md) — Service layer the CLI routes through
- [Plugin System](plugin-system.md) — Dynamic CLI command registration
