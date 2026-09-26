---
id: index-one-reconcile-for-index-build-reindex-and-sync-report-duplicate-ids-adr
title: 'Index: one reconcile for index build, reindex and sync; report duplicate ids (ADR-0038 step 2)'
type: backlog_item
tags:
- architecture
- storage
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: M
rank: 0
---

Step 2 of [[adr-0038]] (proposed). Fixes #485, #486 and #487.

The three index walks reconcile differently. `index_kb` never retires rows. `sync_kb` keys by id and ignores a moved path. Both syncs judge staleness by mtime alone. Duplicate ids flip the row on every sync, and nothing reports them.

## Acceptance criteria
- `index_kb`, `sync_kb` and `sync_incremental` share one reconcile: rows equal the ids of parseable files (I2), unseen rows are retired, and a path change is applied.
- A known path is re-parsed when mtime or size differs from what was indexed (store size, or compare to the hash when both match; the ADR's open question 4 decides).
- Duplicate ids are returned as `duplicates: [{id, paths}]` in the result, printed by `pyrite index sync` and `pyrite index health`. The same file wins every time (the ADR proposes the lexicographically first KB-relative path).
- A second reconcile with no file change reports 0 added, updated and removed (I3).
- `test_storage_invariant[I2]` and `[I3]` XPASS; their xfails are removed.
- Measure sync time on the pyrite KB before and after.

## Footprint
`pyrite/storage/index.py`, `pyrite/cli/index_commands.py`, `pyrite/services/kb_registry_service.py`, `tests/test_storage_invariants.py` (xfails only).

**Model:** opus. **After:** step 1.
