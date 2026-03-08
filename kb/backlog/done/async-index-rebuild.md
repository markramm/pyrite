---
id: async-index-rebuild
type: backlog_item
title: "Add async/queue-based index rebuild"
kind: improvement
status: done
priority: high
effort: M
tags: [storage, indexing, scalability]
links:
- index-manager
- background-embedding-pipeline
---

# Add async/queue-based index rebuild

## Problem

`IndexManager.sync_kb()` is synchronous — it blocks until the full KB is indexed. For large KBs this stalls the CLI and delays API responses. The embedding pipeline already has a background queue pattern, but full index sync does not.

## Solution

Add an async/queue-based rebuild path for index sync, following the pattern established by the background embedding pipeline. Options:

1. **Background thread with progress callback** — simplest, works for CLI and server
2. **Async generator yielding progress** — integrates with FastAPI streaming responses
3. **Queue-based with worker** — matches embedding pipeline, most scalable

Start with option 1 (background thread) and expose a progress endpoint in the API.

## Files

- `pyrite/storage/index.py` — `IndexManager.sync_kb()`
- `pyrite/services/embedding_worker.py` — existing background queue pattern to follow
- `pyrite/cli/index_commands.py` — CLI progress display
- `pyrite/server/endpoints/index_endpoints.py` — async status endpoint
