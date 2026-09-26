---
id: storage-a-file-s-location-is-sticky-across-update-and-rename-adr-0038-step-3
title: "Storage: a file's location is sticky across update and rename (ADR-0038 step 3)"
type: backlog_item
tags:
- architecture
- storage
importance: 5
kind: tech_debt
status: proposed
priority: medium
effort: S
rank: 0
---

Step 3 of [[adr-0038]] (proposed). Fixes #488, the file half of #489, and #493. Open question 1 is decided: a rename changes only the id and never moves a file, for any type; a wrong path is delete + create.

## Acceptance criteria
- "Keep the file in its folder" and "infer the type's folder" are different arguments to `KBRepository.save` (today `subdir=None` means both). An update keeps a KB-root file at the root.
- `KBRepository.rename` rewrites the id in place for every type, never moving the file. `rename(x, x)` is refused with a `ValidationError` (#493). The CLI, MCP and REST rename output and docs say so.
- `test_i6_update_moves_a_root_file` (#488), `test_i6_rename_moves_an_id_named_file` (#489) and `test_i9_rename_to_same_id_leaves_no_row` (#493) XPASS; their markers are removed.

## Footprint
`pyrite/storage/document_manager.py`, `pyrite/storage/repository.py`, `pyrite/services/kb_service.py` (`rename_entry`), rename docs (`docs/`), `tests/test_storage_invariants.py`.

**Model:** sonnet. **After:** step 1.
