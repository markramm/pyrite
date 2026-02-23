---
type: backlog_item
title: "Consolidate CLI Entry Points"
kind: improvement
status: completed
priority: medium
effort: M
tags: [cli, dx]
---

Currently three separate CLIs:
- `pyrite` — argparse-based write CLI (legacy)
- `pyrite-read` — argparse-based read CLI
- `pyrite-admin` — Typer-based admin CLI

Plugin commands (sw, zettel, wiki) register on the Typer app in `pyrite/cli/__init__.py` but this app has no entry point. Should consolidate to a single Typer-based CLI with subcommands and permission flags, or at minimum wire the Typer app as the primary entry point.
