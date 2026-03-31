---
id: worktree-write-routing
type: backlog_item
title: "Route entry writes to user worktree, reads from main"
kind: feature
status: proposed
priority: high
effort: M
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

When a logged-in user edits an entry via the web UI or API, the write needs to go to their personal worktree (on branch `user/{name}`), not to the main branch. Reads should continue to come from main so everyone sees the canonical content.

## Scope

- Request-scoped KB path resolution in the API layer
- For authenticated write requests: resolve KB path to the user's worktree
- For read requests: resolve to the main branch working directory
- Entry CRUD endpoints (create, update, delete) use the routed path
- User sees their own edits in the worktree's index
- Auto-commit on save (commit to user branch with entry title as message)

## Acceptance Criteria

- Unauthenticated/read-only users see main branch content
- Authenticated users writing entries see changes in their worktree
- Worktree index stays in sync with user's edits
- No changes to main branch from user edits
