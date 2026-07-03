---
id: verify-after-write-on-the-index-path
title: Verify-after-write on the index path
type: backlog_item
tags:
- tech-debt
- reliability
- index
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: M
rank: 0
---

## Problem

The files-vs-index seam has no post-write verification: an entry write that succeeds on disk but fails to index (or indexes a stale/empty body) is downgraded to a warning and discovered only at the next manual `index sync`. Concrete sites:

- `kb_service.py` rename path (~line 591): `sync_incremental` failure after a rename is caught broadly and logged as a warning, leaving the index resolving the old ID.
- `repository.py`: ~8 `except Exception -> logger.warning` sites on the parse path silently drop entries from index coverage.
- No read-back check anywhere on the write path confirms the indexed row matches the file just written (the historical `search --include-body` empty-body bug was this seam).

## Proposal

After any write that triggers indexing (create/update/rename/delete), read the indexed row back and verify id, file_path, and non-empty body match the file. On mismatch or index failure, surface a hard error (or a structured degraded-state result), not a log-level warning. Consider a `--no-verify` escape hatch for bulk operations.

## Progress

- [x] **Content-hash staleness** (caa3902, 2026-07-03) — added `entry.content_hash` (SHA-256, migration v21), computed on every indexing write, compared in `check_health()`'s new `content_changed` finding. Closes the same-second-edit gap: `check_staleness()` deliberately stays mtime-only (cheap, safe on every search call per its documented cost contract); hash comparison lives in `check_health()` instead, which already reads every file's bytes per entry so hashing there is nearly free. Wired into `pyrite index health` CLI (JSON + rich text, counts toward `unhealthy`).
- [x] **Rename-path read-back verification** (318037f, 2026-07-03) — `KBService.rename_entry` now reads back `db.get_entry(new_id, kb_name)` after `sync_incremental` and raises `StorageError` (not a swallowed warning) on either a sync exception or a failed read-back. Result gains `index_verified: true` on success. File rename is never rolled back — only the index side is treated as degraded, with a `pyrite index sync` recovery hint in the error message. This closes the one concrete site named in the ticket; the other ~8 `repository.py` parse-path sites (below) are the same pattern applied to create/update/delete.
- [ ] Convert the ~8 `repository.py` `except Exception -> logger.warning` sites on the parse path to hard errors / structured degraded-state results
- [ ] `--no-verify` escape hatch for bulk operations

## Notes

This is the second half of the derived-state-synchronization fix; the first half (registry enumeration via all_kbs()) landed with tests/test_index_covers_db_registered_kbs.py. See also [[collapse-kb-registry-to-one-source-of-truth]].

Prerequisite for [[epic-shared-instance-readiness]]: invited peers must never hit the silent-index class the operator works around from muscle memory.

