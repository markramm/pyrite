---
id: storage-documentmanager-owns-every-file-and-row-transition-adr-0038-step-5
title: 'Storage: DocumentManager owns every file-and-row transition (ADR-0038 step 5)'
type: backlog_item
tags:
- architecture
- storage
importance: 5
kind: tech_debt
status: proposed
priority: medium
effort: M
rank: 0
---

Step 5 of [[adr-0038]] (proposed). One owner for every file-and-row transition.

Today, rename bypasses `DocumentManager` and then runs a full `sync_incremental` of the KB. Delete calls `KBRepository.delete` directly. The rule for where an undeclared key goes lives in both `build_entry` and `KBService._update` (#447).

## Acceptance criteria
- `DocumentManager` owns create, update, rename and delete of file and row together. Rename writes its two rows directly (I9 without a full sync).
- One function decides where an undeclared key goes, called by create and by update.
- A structural test fails if `KBRepository.save`, `.delete` or `.rename` is called from outside `pyrite/storage/`. It starts with a shrinking allowlist, in the style of ADR-0037 §5.
- The whole storage-invariant file passes with no xfail left.

## Footprint
`pyrite/storage/document_manager.py`, `pyrite/services/kb_service.py` (rename, delete, update bodies only; no signature change, see ADR-0037 decision 3), `pyrite/models/factory.py`, a new guard test.

**Model:** opus. **After:** steps 2 and 4.
