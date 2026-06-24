---
id: duplicate-entry-ids-across-backlog-and-done
title: "Duplicate entry-id files: same id present in both kb/backlog/ and kb/backlog/done/"
type: backlog_item
tags: [kb-hygiene, index, backlog, data-cleanup]
importance: 5
kind: bug
status: done
priority: medium
effort: S
rank: 0
---

## Problem

The `pyrite` KB has at least 4 entry ids that exist as **two files on disk** — one
in the active dir and one in `done/` (or `notes/`). `list_files()` yields 679 files
but only 675 distinct ids are indexed, because the index is keyed by id and the
duplicate silently loses. Discovered while building `check_staleness()` for
`[[search-stale-index-silent]]`.

Confirmed duplicates (each id at two paths):

- `web-ui-git-operations` — `kb/backlog/` + `kb/backlog/done/`
- `oauth-providers` — `kb/components/` + `kb/backlog/done/`
- `odm-layer` — `kb/designs/` + `kb/backlog/done/`
- `plugin-developer-guide` — `kb/notes/` + `kb/backlog/done/`

## Root cause (suspected)

Residue from the status-update placement bug (gotchas.md / the `kb/notes/`
auto-replacement issue): when an item was marked done, the CLI wrote a fresh copy
to the type's default subdir without removing the original, leaving two files with
the same id. Whichever indexes last wins; the other is dead weight and confuses any
count-based tooling.

## Fix

1. Identify all duplicate-id pairs (script: group `list_files()` by parsed id, flag
   ids with >1 path).
2. For each pair, keep the correct location (active vs `done/` per the item's real
   status) and `git rm` the stale copy.
3. Re-sync the index; confirm `list_files()` count == indexed count.
4. Consider a `pyrite index health` check that flags duplicate ids on disk so this
   can't accumulate silently (today health checks unindexed/stale/missing but not
   duplicate-id-across-paths).

## Provenance

Discovered 2026-06-23 while implementing `[[search-stale-index-silent]]` — the
file-count-vs-indexed-count divergence turned out to be duplicate ids, not staleness.
Related to the placement bug tracked in the daily-capture/pyrite-dev gotchas.
