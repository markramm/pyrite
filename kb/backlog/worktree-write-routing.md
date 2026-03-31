---
id: worktree-write-routing
type: backlog_item
title: "Route entry writes to user worktree, reads from main"
kind: feature
status: done
priority: high
effort: L
tags: [core, git, collaboration, api]
links:
- target: epic-fork-system
  relation: subtask_of
  kb: pyrite
- target: worktree-service
  relation: blocked_by
  kb: pyrite
- target: adr-0024
  relation: tracks
  kb: pyrite
---

## Problem

When a logged-in user edits an entry via the web UI or API, the write needs to go to their personal worktree (on branch `user/{name}`), not to the main branch. Reads should continue to come from main so everyone sees the canonical content. The hard part is **search**: users must find their own edits but not see other users' unmerged work.

## Scope

### File routing
- Request-scoped KB path resolution in the API layer
- For authenticated write requests: resolve KB path to the user's worktree
- For read requests: resolve to the main branch working directory
- Entry CRUD endpoints (create, update, delete) use the routed path
- Auto-commit on save (commit to user branch with entry title as message)

### Search: diff index overlay (20-50 users)
- Main index is shared for all reads (canonical content)
- Each user gets a small **diff index** (separate SQLite DB) containing only their changed/created entries
- Search queries merge main + diff: query both, user's version wins on entry ID collision
- Implementation: `OverlaySearchBackend` wrapping main `SearchBackend` + user diff `SearchBackend`
- Diff index updated on each user save via existing `IndexManager`
- On merge to main: diff entries promoted to main index, user diff DB cleared
- Embeddings: only re-embed changed entries in the diff index, share main's vectors for everything else

### Why diff index (not per-user full index)
- Full index per user = 50 × 50MB = 2.5GB, plus embedding vectors. Works but wasteful.
- Diff index per user = a few KB to a few MB (only their edits). Near-zero overhead.
- Main index handles 99% of search load. Diff is a thin overlay.

## Acceptance Criteria

- Unauthenticated/read-only users see main branch content
- Authenticated users see main + their own edits in search, entry lists, and graph
- Users do NOT see other users' unmerged edits
- Worktree diff index stays in sync with user's edits
- No changes to main branch index from user edits
