---
type: backlog_item
title: "Remove Legacy Files and Stale Entry Points"
kind: improvement
status: proposed
priority: medium
effort: S
tags: [cleanup, dx]
---

Several files remain from the upstream Zettelkasten project and the pre-rename era:

- `pyrite/read_cli.py` — argparse CLI, references `crk-read` throughout, links to upstream docs
- `pyrite/write_cli.py` — argparse CLI, references `crk-read`/`crk-write`
- `cascade_research.egg-info/` — stale egg-info from pre-rename
- `requirements.txt` — says "cascade-research dependencies", mixes dev/runtime deps, out of sync with pyproject.toml

The `pyrite-read` entry point in `pyproject.toml` still points to the legacy argparse CLI.

The `cli-entry-point-consolidation.md` backlog item is marked "done" but these files and entry points remain. Clean them up.
