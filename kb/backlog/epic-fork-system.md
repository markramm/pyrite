---
id: epic-fork-system
type: backlog_item
title: "Epic: Multi-User Git Collaboration System"
kind: epic
status: in_progress
priority: high
effort: L
tags: [web, collaboration, git]
links:
- target: adr-0024
  relation: tracks
  kb: pyrite
- target: worktree-service
  relation: has_subtask
  kb: pyrite
- target: worktree-write-routing
  relation: has_subtask
  kb: pyrite
- target: worktree-merge-queue
  relation: has_subtask
  kb: pyrite
---

## Problem

Hosting a shared Pyrite instance for multiple investigators requires multi-user editing without external dependencies. Contributors log in, edit entries on their own git worktree branch, and submit changes for admin review. No GitHub accounts or fork management needed.

## V1 Scope (ADR-0024)

Uses git worktrees for zero-copy per-user isolation with an in-app admin merge queue. All KBs public, all reads from main, writes to per-user branches.

## Subtasks

1. [[worktree-service]] — WorktreeService: create/list/reset/delete per-user worktrees
2. [[worktree-write-routing]] — Route entry writes to user's worktree, reads from main
3. [[worktree-merge-queue]] — Admin merge queue UI: list submitted, diff, merge, reject

## Deferred to V2

- [[per-user-fork-directories]] — Full fork system (ADR-0018)
- [[fork-divergence-indicators]] — UI divergence indicators
- [[fork-conflict-resolution-ui]] — Visual conflict resolution
- [[sync-conflict-resolution-ui]] — Git sync conflict resolution
- [[web-ui-git-operations]] — General git operations panel (V1 uses submit/merge instead)
