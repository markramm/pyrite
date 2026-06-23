---
id: search-status-filter-cli
type: backlog_item
title: "Wire --status metadata filter into the CLI search command"
tags: [cli, search, status]
kind: feature
status: proposed
priority: high
effort: S
---

## Problem

`pyrite search` (and the `kb` wrapper) has no `--status` filter, even though the
underlying capability already exists. `kb search -k daily-capture-reports --status unprocessed`
errors with `No such option: --status` and suggests `--state` (the US-state column,
which is empty for most KBs → 0 results). This silently mislead a live daily-capture run
into thinking the unprocessed queue was empty when 23/28 rows were correctly indexed as
`unprocessed`.

The query layer is already built and exposed everywhere *except* the CLI search path:

- `find_by_status()` query method — `pyrite/storage/queries.py:379`
- Wired to MCP as `kb_find_by_status` — `pyrite/server/mcp_server.py:657,662`
- But `pyrite/cli/search_commands.py` has no `--status` option, and
  `db.search()` (`pyrite/storage/backends/sqlite_backend.py:142`) takes no status
  param and never filters `e.status`.

KB-type agnostic — affects any workflow that queries by lifecycle status (ledgers,
draft queues, task-like KBs).

## Fix

Add `--status` to the `search` command and a `status` param to `db.search()`
(`AND e.status = ?`), **or** expose a `pyrite find-by-status` command that wraps the
existing `find_by_status()` query. Prefer the former for discoverability — users reach
for `search --status` first.

## Provenance

Diagnosed 2026-06-23 from a live daily-capture run. Filed from the daily-capture skill's
PYRITE-FEATURE-REQUESTS.md (Search Bug S1).

## Workaround

Read ledger files on disk directly (`grep '^status:'`), which is authoritative. Do not
trust `kb search --status` for the unprocessed queue until this is wired.
