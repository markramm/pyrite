---
id: history-by-id-rename-records-previous-ids-attribution-checks-the-id-at-every
title: 'History by id: rename records previous_ids; attribution checks the id at every commit (ADR-0038 step 4)'
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

Step 4 of [[adr-0038]] (proposed). Fixes the history half of #489, and #490.

`_same_entry_history` and `VersionService.record_commit` compare ids only where the path changes. So an in-place id change inherits another entry's history, and a rename that moves a file loses its own.

## Acceptance criteria
- A rename appends the old id to a managed `previous_ids` frontmatter list (in `_MANAGED_FIELDS`; an update cannot set it). The ADR's open question 2 decides between this and `aliases`.
- History attribution checks the id at every commit: a commit belongs to X when the file held X or one of X's `previous_ids`.
- Renaming moves the old id's `entry_version` rows to the new id before the old row is retired (today the FK cascade drops them).
- All three I10 tests pass, and their xfails are removed.

## Footprint
`pyrite/storage/index.py` (`_same_entry_history`, `index_with_attribution`), `pyrite/services/version_service.py`, `pyrite/storage/repository.py` (`rename`), `pyrite/services/kb_service.py` (`_MANAGED_FIELDS`), `pyrite/storage/crud.py` or its backend (moving version rows).

**Model:** opus. **After:** step 3.
