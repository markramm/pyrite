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

Step 3 of [[adr-0038]] (proposed). Fixes #488 and the file half of #489. **Blocked on the ADR's open question 1** (does a rename ever move a file?).

## Acceptance criteria
- "Keep the file in its folder" and "infer the type's folder" are different arguments to `KBRepository.save` (today `subdir=None` means both). An update keeps a KB-root file at the root.
- If the maintainer takes option (a): `KBRepository.rename` rewrites the id in place for every type, never moving the file. The CLI, MCP and REST rename output and docs say so.
- `test_storage_invariant[I6]` XPASSes; its xfail is removed. If option (b) is taken, the I6 rename check is relaxed to "moves only `<old>.md` to `<new>.md`", and the ADR is edited to match.

## Footprint
`pyrite/storage/document_manager.py`, `pyrite/storage/repository.py`, rename docs (`docs/`), `tests/test_storage_invariants.py`.

**Model:** sonnet. **After:** step 1 and ADR-0038 accepted.
