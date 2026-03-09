---
id: cli-entry-point-consolidation
title: "Consolidate CLI Entry Points"
type: backlog_item
tags: [cli, dx]
kind: improvement
status: done
effort: M
---

Currently three separate CLIs:
- `pyrite` — argparse-based write CLI (legacy)
- `pyrite-read` — argparse-based read CLI
- `pyrite-admin` — Typer-based admin CLI

Plugin commands (sw, zettel, wiki) register on the Typer app in `pyrite/cli/__init__.py` but this app has no entry point. Should consolidate to a single Typer-based CLI with subcommands and permission flags, or at minimum wire the Typer app as the primary entry point.
