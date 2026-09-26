---
id: storage-one-id-reader-find-file-looks-up-by-id-not-by-filename-adr-0038-step-1
title: 'Storage: one id reader; find_file looks up by id, not by filename (ADR-0038 step 1)'
type: backlog_item
tags:
- architecture
- storage
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: S
rank: 0
---

Step 1 of [[adr-0038]] (proposed). Fixes #483 and #484.

Lookup and loading disagree on which id a file holds. `KBRepository.find_file` returns a filename hit without reading it, and its fallback scan compares only an explicit `id:` with a naive delimiter. The loader derives an id from the title when `id:` is missing.

## Acceptance criteria
- One function answers "which id does this file hold", the loader's (explicit `id:`, else derived). `find_file`'s scan, `entry_id_from_markdown`, and create's exists check use it.
- `find_file(x)` verifies a filename hit and returns only a file holding `x`; when exactly one file holds `x`, it finds it.
- The scan's skip rules equal `list_files`'s (today the scan also skips `_`-prefixed folders).
- `test_storage_invariant[I1]`, `[I4]`, `[I7]` XPASS, and their xfails are removed. `[I8]` XPASSes too, or is re-pointed only at what remains.
- Measure `find_file` on the pyrite KB (about 2,000 entries), hit and miss, before and after; report the numbers in the PR.

## Footprint
`pyrite/storage/repository.py`, `pyrite/models/core_types.py`, `tests/test_storage_invariants.py` (xfails only), a focused regression test per issue.

**Model:** sonnet. **After:** step 0.
