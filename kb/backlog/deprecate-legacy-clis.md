---
id: deprecate-legacy-clis
type: backlog_item
title: "Deprecate and remove pyrite/admin_cli.py and pyrite/read_cli.py"
kind: refactor
status: proposed
priority: low
effort: M
tags: [cli, refactor, dead-code]
---

## Problem

Three separate CLI entry points exist:

- `pyrite/cli/__init__.py` (~820 LOC) — primary CLI; sub-apps for kb,
  index, entry, search, export, task, etc.
- `pyrite/admin_cli.py` (~654 LOC) — DB schema, KB init, backups, plugin
  management
- `pyrite/read_cli.py` (~316 LOC) — read-only CLI (get, list, timeline,
  tags, backlinks, config show)

Tests cover all three (`test_admin_cli.py`, `test_read_cli.py`,
`test_cli_commands.py`). They are not stranded — they work — but the
functional overlap with `pyrite/cli/*_commands.py` modules is substantial
and the split has no documented rationale today.

The audit found no callers requiring the `admin_cli` / `read_cli` entry
points specifically; they appear to be archaeology from before the
`pyrite/cli/` package was extracted.

## Solution

1. Audit each `admin_cli` and `read_cli` command. For each:
   - Does an equivalent exist in `pyrite/cli/`?
   - If yes: confirm parity, remove the legacy command.
   - If no: port it into the appropriate `pyrite/cli/*_commands.py`.
2. Mark `admin_cli` and `read_cli` as deprecated for one release (print a
   warning when invoked) and document the replacement command.
3. Remove in the following release.
4. Move the relevant tests into `test_cli_commands.py` (or the per-feature
   test file) and delete `test_admin_cli.py` / `test_read_cli.py` shells.

## Acceptance criteria

- All `admin_cli` / `read_cli` commands have a documented `pyrite ...`
  replacement.
- Deprecation warnings land in a tagged release.
- Final removal in the release after.
- Test coverage maintained (no net coverage loss).

## Out of scope

- Major CLI redesign / top-level command reorganization (see separate
  `cli-top-level-reorg` ticket if created).

## Related

- `consistent-kb-flag-across-commands` — adjacent CLI hygiene work
