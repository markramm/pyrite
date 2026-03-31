---
id: worktree-service
type: backlog_item
title: "WorktreeService: per-user git worktree management"
kind: feature
status: proposed
priority: high
effort: M
tags: [core, git, collaboration]
links:
- target: epic-fork-system
  relation: subtask_of
  kb: pyrite
- target: adr-0024
  relation: tracks
  kb: pyrite
---

## Problem

Multi-user editing requires per-user isolation. Git worktrees provide zero-copy working directories on separate branches, sharing the object store with the main repo.

## Scope

New `WorktreeService` class with methods:

- `create_worktree(kb_name, username)` — `git worktree add .git/worktrees/user-{name} -b user/{name}`
- `get_worktree_path(kb_name, username)` — return path to user's worktree (or None)
- `ensure_worktree(kb_name, username)` — create if not exists, return path
- `list_worktrees(kb_name)` — list all user worktrees for a KB
- `reset_to_main(kb_name, username)` — rebase or reset user branch to main
- `delete_worktree(kb_name, username)` — `git worktree remove`
- Per-worktree search index (separate SQLite DB per worktree)

## Acceptance Criteria

- Worktrees created on demand, persist across requests
- Each worktree has its own search index
- Inactive worktrees can be cleaned up (GC)
- Works with all registered KBs that have git repos
