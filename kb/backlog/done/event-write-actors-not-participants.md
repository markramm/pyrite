---
id: event-write-actors-not-participants
title: "EventEntry writes participants: but the timeline convention is actors:"
type: backlog_item
tags: [models, events, frontmatter, convention]
importance: 5
kind: bug
status: done
priority: medium
effort: S
rank: 0
---

## Problem

`EventEntry` reads both `actors` and `participants` from frontmatter but always *writes*
`participants`. Round-tripping a cascade-timeline event through pyrite silently renames the
field, diverging from the established convention used by ~4,500 existing files (and
CONTRIBUTING.md) which use `actors`.

Verified at runtime: an event loaded with `actors: [Alice, DOJ]` serializes back out as
`participants: [Alice, DOJ]`.

Location:
- Writes `participants` — `pyrite/models/core_types.py:161` (`to_frontmatter`)
- Reads both, legacy-aware — `pyrite/models/core_types.py:174` (`from_frontmatter`)

This is why the daily-capture skill writes markdown files directly instead of using
`pyrite create` — to avoid emitting `participants:` files that don't match the corpus.

## Fix

Write `actors` in frontmatter (matching the established convention) while keeping
`participants` as the internal Python property name. Before flipping, confirm the indexer,
renderers, and any extension readers consume `actors` consistently so the rename doesn't
break read paths.

## Provenance

Filed from the daily-capture skill's PYRITE-FEATURE-REQUESTS.md (Remaining Issue #5). The
other original issues (#1 subdirectory `""`, #2 publisher/tier preservation, #3 `--status`
write, #4 `--importance` write) are already fixed in current source as of 2026-06-23; #6
bulk directory import is tracked by `[[bulk-import-from-directory]]`.
