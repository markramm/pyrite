---
id: verify-after-write-on-the-index-path
title: Verify-after-write on the index path
type: backlog_item
tags:
- tech-debt
- reliability
- index
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

## Notes

This is the second half of the derived-state-synchronization fix; the first half (registry enumeration via all_kbs()) landed with tests/test_index_covers_db_registered_kbs.py. See also [[collapse-kb-registry-to-one-source-of-truth]].
