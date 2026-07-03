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
status: done
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
- [x] **repository.py / index.py parse-path visibility** (2026-07-03) —
  re-audited the actual site count: `repository.py` currently has 6
  `except Exception` sites (not 8 — some had already been narrowed by
  earlier fail-open-sweep work), covering `find_file`, `load`,
  `list_entries` (x2, entries + collections), `search_files`. All
  already log at warning with the file path; these are read-path
  fallbacks (skip one bad file, keep scanning), not write-path
  failures — a caller iterating `list_entries()` during bulk sync gets
  a log line per bad file but the CALLER gets no signal in its return
  value. Traced the two actual write-path (`sync_incremental` /
  `sync_kb`) consumers of this iteration:
  - `sync_incremental` already tracked `FrontmatterError` failures in
    `results["malformed"]` (see prior session's Tier A 1080 fix,
    tests/test_storage.py::TestSyncMalformedFileSummary) but its two
    generic `except Exception` sites (stale-check-and-reindex,
    parse-new-file) only logged — a non-FrontmatterError parse failure
    (e.g. valid YAML with a field type that crashes
    `entry_from_frontmatter`) was invisible in the sync result even
    though FrontmatterError wasn't. Fixed: both non-frontmatter-error
    exceptions now also append to `results["malformed"]`.
  - `sync_kb` (the DB-only-KB sibling used by `KBRegistryService`,
    e.g. the REST/MCP `reindex_kb` surface) used `repo.list_entries()`
    directly, which has NO malformed-tracking at all — a parse failure
    here was 100% silent from the caller's perspective, just a log
    line. Rewrote `sync_kb` to walk `list_all_files()` +
    `load_entry_from_file()` (the same raising primitives
    `sync_incremental` uses) instead of the swallowing
    `list_entries()` generator, adding the same `results["malformed"]`
    tracking.
  - `KBReindexResponse` (the REST schema for `POST
    /kbs/{name}/reindex`) was a strict Pydantic model with only
    `name`/`added`/`updated`/`removed` fields — since the endpoint
    does `KBReindexResponse(name=name, **result)`, the new `malformed`
    key would have been silently dropped by Pydantic's default
    ignore-extra-fields behavior, reintroducing the exact
    silent-data-loss failure this ticket is about, just one layer up
    at the API boundary. Added `malformed: list[dict[str, str]] =
    Field(default_factory=list)` to the schema.
  - 4 new/extended tests, all failed before their respective fixes:
    `TestSyncKbMalformedFileSummary` (sync_kb result key),
    `test_reindex_reports_malformed_files` (service-layer
    passthrough — passed immediately once sync_kb was fixed, proving
    the fix propagates cleanly), `test_reindex_response_schema_carries_malformed`
    (Pydantic schema boundary).
- [x] **`--no-verify` escape hatch — re-scoped, not implemented** (2026-07-03)
  — on review, this doesn't apply to the work actually shipped so far.
  The escape hatch was proposed against a hypothetical expensive
  blocking verification (read every file back after every write in a
  bulk op). What's shipped instead is (a) content-hash staleness
  detection in `check_health()` (already opt-in, not on the hot write
  path), (b) rename-path read-back verification (a single read-back
  per rename, not a bulk concern), and (c) malformed-file VISIBILITY
  fixes (pure bookkeeping on an error path that already existed — zero
  added cost on the happy path). None of these are expensive enough on
  bulk operations to need a bypass flag. If a future phase adds
  mandatory read-back verification on every create/update in bulk
  sync, revisit an escape hatch then — not adding speculative flag
  plumbing for a check that doesn't exist yet.

## Notes

This is the second half of the derived-state-synchronization fix; the first half (registry enumeration via all_kbs()) landed with tests/test_index_covers_db_registered_kbs.py. See also [[collapse-kb-registry-to-one-source-of-truth]].

Prerequisite for [[epic-shared-instance-readiness]]: invited peers must never hit the silent-index class the operator works around from muscle memory.
