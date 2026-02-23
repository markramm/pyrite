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
- `pyrite` — Write-tier (argparse-based, CRUD operations)
- `pyrite-read` — Read-only (safe for agents)
- `pyrite-admin` — Admin (KB management, indexing, repos, auth)

## Typer App (pyrite/cli/__init__.py)
The Typer-based app provides the richest interface:
- `kb` subcommand: list, add, remove, discover, validate
- `index` subcommand: build, sync, stats, embed, health
- `repo` subcommand: add, remove, subscribe, fork, sync
- `auth` subcommand: github-login, whoami, status
- Plugin sub-apps registered dynamically (e.g., `sw`, `zettel`, `wiki`)
