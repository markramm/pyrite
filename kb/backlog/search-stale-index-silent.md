---
id: search-stale-index-silent
type: backlog_item
title: "Search queries a stale index silently — no staleness warning on the search path"
tags: [search, index, correctness]
kind: bug
status: proposed
priority: high
effort: M
---

## Problem

Search can return a confidently-wrong stale view with no warning. On a live run the index
was last built 2026-06-11 while 5429 files existed on disk (9 unindexed + 10 updated);
search returned the 12-day-old view silently. A manual `kb index sync` fixed it
(Added 9, Updated 10).

This is a **correctness** bug, not a UX nit — the search result looked authoritative but
was 12 days out of date.

Root cause:
- Staleness detection exists (`_is_stale`, `pyrite/storage/index.py:560`) but only inside
  `index health`.
- The search path never consults it — `pyrite/cli/search_commands.py:77` only
  force-indexes when the index is *entirely empty* (`count_entries() == 0`), never on
  partial staleness.

### Related: dual-index split (upstream root)

The `kb` wrapper sets `PYRITE_CONFIG_DIR=/Users/markr/kb`, so it reads/writes
`/Users/markr/kb/index.db`, NOT `~/.pyrite/index.db` used by bare `pyrite`. The two
commands query different indexes, which makes silent staleness easier to hit and
corroborates `bug_pyrite_silent_index_failure`. Worth resolving alongside this so both
share one index.

## Fix

On search, cheaply compare the max on-disk mtime per KB against `MAX(indexed_at)` and emit
a stderr warning (keep it OFF stdout to preserve `--format json`), optionally auto-syncing.
Resolve the `kb` vs bare-`pyrite` dual-DB split.

## Provenance

Diagnosed 2026-06-23 from a live daily-capture run (it was the root trigger of that
session). Filed from the daily-capture skill's PYRITE-FEATURE-REQUESTS.md (Search Bug S3).

## Workaround

Run `kb index sync -k <kb>` at the START of every daily-capture run, before any search or
dedup check. Now reflected in the daily-capture SKILL.md Step 1.
