---
id: add-backward-status-transitions-for-backlog-items
title: Add backward status transitions for backlog items
type: backlog_item
tags:
- workflow
- software-kb
kind: improvement
status: done
priority: high
assignee: claude
effort: S
---

## Problem

The backlog workflow only allows forward transitions in most cases. Practical scenarios require backward transitions:

- `accepted → proposed` — demote an item back to backlog (e.g., external blocker discovered after acceptance)
- `accepted → deferred` — defer an accepted item that can't proceed
- `in_progress → accepted` — unclaim/abandon work without submitting for review

Currently the only way to handle situations like an externally-blocked accepted item is to add notes to the entry body, since the workflow won't allow moving it back.

## Impacted Files

- `extensions/software-kb/src/pyrite_software_kb/workflows.py` — add transitions to `BACKLOG_WORKFLOW`
- `extensions/software-kb/tests/test_software_kb.py` — add test coverage for new transitions

## Acceptance Criteria

- `accepted → proposed` transition exists (requires reason)
- `accepted → deferred` transition exists
- `in_progress → accepted` transition exists (requires reason, clears assignee)
- All new transitions require `write` permission
- Backward transitions that lose work context require a reason
- Existing tests still pass
- New transitions have test coverage
