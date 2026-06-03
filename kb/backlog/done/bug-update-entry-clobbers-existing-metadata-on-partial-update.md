---
id: bug-update-entry-clobbers-existing-metadata-on-partial-update
type: backlog_item
title: "BUG: kb_service.update_entry clobbered existing metadata keys on partial update"
kind: bug
status: done
priority: high
effort: XS
tags: [bug, kb_service, metadata, data-loss, review-flow, entries]
---

## Problem

`KBService.update_entry(metadata={...})` replaced the entire metadata dict
whenever a caller passed `metadata=`. Any partial update silently dropped
**all** other metadata keys the entry already carried.

Surfaced while wiring the review-flow feature: a UI action that wrote just
`metadata={"review_comments": [...]}` blew away every prior metadata key on
the entry (`extra_fields`, prior workflow markers, etc.) — silent data loss
with no error.

## Impact

- Any caller doing partial metadata writes lost data: REST `PATCH /entries`,
  MCP `kb_update`, the in-flight review-flow UI, any agent or script.
- The damage was silent — the write returned success and the response
  reflected only the newly-written keys, so a downstream read looked
  "correct" until you cross-referenced the pre-existing keys.

## Root cause

`pyrite/services/kb_service.py:455` did a flat `setattr(entry, "metadata",
value)` inside the field-update loop. Metadata is a bag (a dict by design),
not a scalar field — the set-and-forget shape was wrong for it.

## Fix

Shallow-merge dict-typed metadata updates into the existing bag; non-dict
updates still overwrite (the normal field-set path). Implementation in
commit `d0e2677`.

```python
if key == "metadata" and isinstance(value, dict):
    merged = dict(getattr(entry, "metadata", None) or {})
    merged.update(value)
    setattr(entry, key, merged)
else:
    setattr(entry, key, value)
```

Regression test `test_update_entry_merges_metadata` in `tests/test_integration.py`
seeds a key, partial-updates a different key, asserts both survive, and
reloads from disk to confirm the merge persisted to frontmatter.

## Related

- `bug-rest-update-endpoint-silently-dropped-metadata` — companion bug
  surfaced in the same review-flow integration pass; the REST layer was
  swallowing `metadata` before this service-layer bug could even be hit.
- Fix commit: `d0e2677` (also carries the REST-wiring fix).
