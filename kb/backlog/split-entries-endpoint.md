---
id: split-entries-endpoint
type: backlog_item
title: "Split pyrite/server/endpoints/entries.py (802 LOC) into read/write modules"
kind: refactor
status: proposed
priority: low
effort: S
tags: [refactor, api, code-quality]
---

## Problem

`pyrite/server/endpoints/entries.py` is 802 LOC handling 32 routes. It mixes:

- GET / list / search (read tier)
- POST / PATCH / DELETE (write tier)
- Bulk operations
- Worktree overlay routing
- Wikilink utilities

Reading the file requires keeping all of these in your head. Authorization
review is harder than it needs to be because read paths and write paths
are interleaved.

## Solution

Split into:

```
pyrite/server/endpoints/
├── entries_read.py    # GET, list, search, batch-read
├── entries_write.py   # POST, PATCH, DELETE, bulk-mutate
└── entries.py         # router that mounts both (or remove if FastAPI
                       #   include_router suffices)
```

Co-locate the auth dependency on each file's router so the tier check is
obvious from the imports.

## Acceptance criteria

- `entries.py` shrinks substantially (or is replaced by a thin re-export).
- Each new file under 500 LOC.
- Route paths unchanged, OpenAPI schema unchanged.
- All existing tests pass.
- Auth review can be done by reading `entries_write.py` alone.

## Related

- `split-mcp-server-module` — same pattern on the MCP side
