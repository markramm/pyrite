---
id: bug-rest-update-endpoint-silently-dropped-metadata
type: backlog_item
title: "BUG: REST PATCH /entries silently dropped `metadata` from request and response"
kind: bug
status: done
priority: high
effort: XS
tags: [bug, rest-api, entries, schema, metadata, review-flow]
---

## Problem

The REST entry-update endpoint accepted `metadata` in the request schema
but **never forwarded it to the service** — `req.metadata` was filtered out
before the service call. `EntryResponse` did not include `metadata` either,
so even a successful write was invisible to read-back.

## Impact

- Any REST client setting metadata appeared to succeed (200 OK) but the
  write never reached storage. Worse, the response didn't expose metadata,
  so a client couldn't even detect the omission without reading the file
  directly.
- Hit immediately when wiring the review-flow web UI — comment-write calls
  returned success and the UI updated optimistically, then a refresh
  revealed nothing had persisted.

## Root cause

Two missing wires in `pyrite/server/`:

- `endpoints/entries.py:706` (the `update_entry` handler) iterated the
  optional fields from the request into a `updates` dict but had no
  `if req.metadata is not None: updates["metadata"] = req.metadata` line.
- `schemas.py:130` (`EntryResponse`) had `outlinks`, `backlinks`, `tags`,
  etc. as response fields but no `metadata`.

## Fix

Wire `metadata` through both directions. Implementation in commit `d0e2677`:

```python
# entries.py — pass metadata to the service
if req.metadata is not None:
    updates["metadata"] = req.metadata

# schemas.py — expose metadata in responses
class EntryResponse(BaseModel):
    ...
    metadata: dict = {}
```

The same commit also fixes the companion bug
`bug-update-entry-clobbers-existing-metadata-on-partial-update` — without
that fix this one would have shipped data-loss; with both, the REST PATCH
round-trip works correctly.

## Related

- `bug-update-entry-clobbers-existing-metadata-on-partial-update` —
  companion fix in the same commit.
- Fix commit: `d0e2677`.
