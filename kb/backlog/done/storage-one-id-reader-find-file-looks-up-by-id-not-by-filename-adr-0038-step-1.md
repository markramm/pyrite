---
id: storage-one-id-reader-find-file-looks-up-by-id-not-by-filename-adr-0038-step-1
title: 'Storage: one id reader; find_file looks up by id, not by filename (ADR-0038 step 1)'
type: backlog_item
tags:
- architecture
- storage
importance: 5
kind: tech_debt
status: done
priority: high
effort: S
rank: 0
assignee: agent:pyrite-worker
---

Step 1 of [[adr-0038]] (proposed). Fixes #483, #484 and #494.

Lookup and loading disagree on which id a file holds. `KBRepository.find_file` returns a filename hit without reading it, and its fallback scan compares only an explicit `id:` with a naive delimiter. The loader derives an id from the title when `id:` is missing.

## Acceptance criteria
- One function answers "which id does this file hold", the loader's (explicit `id:`, else derived). `find_file`'s scan, `entry_id_from_markdown`, and create's exists check use it.
- `find_file(x)` verifies a filename hit and returns only a file holding `x`; when exactly one file holds `x`, it finds it.
- The scan's skip rules equal `list_files`'s (today the scan also skips `_`-prefixed folders).
- Delete removes every file that holds the id (#494), or refuses with their paths.
- The per-bug tests for #483 (`test_i4_…`, `test_i7_…`, `test_i8_find_file_trusts_the_filename`), #484 (`test_i1_…`, `test_i8_derived_id_is_not_findable`) and #494 (`test_i9_delete_of_a_duplicated_id_…`) XPASS, and their markers are removed.
- Measure `find_file` on the pyrite KB (about 2,000 entries), hit and miss, before and after; report the numbers in the PR.

## Footprint
`pyrite/storage/repository.py`, `pyrite/models/core_types.py`, `pyrite/storage/document_manager.py` (delete), `tests/test_storage_invariants.py` (xfails only), a focused regression test per issue.

**Model:** sonnet. **After:** step 0.
