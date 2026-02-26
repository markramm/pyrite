---
id: collections-cli-commands
title: Collections CLI Commands
type: component
kind: cli
path: pyrite/cli/collection_commands.py
owner: core
dependencies: [kb-service, collection-query-service]
tags:
- cli
- collections
---

Typer sub-app providing collection management commands under `pyrite collections`.

Commands:
- `pyrite collections list` — list all collections with entry counts, KB name, and source type
- `pyrite collections query "type:backlog_item status:proposed"` — ad-hoc inline query evaluation with result display

Registered in `pyrite/cli/__init__.py` as the `collections` subcommand.
