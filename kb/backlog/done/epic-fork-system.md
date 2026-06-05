---
id: epic-fork-system
title: "Epic: Multi-User Git Collaboration System"
type: backlog_item
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
importance: 5
kind: epic
status: done
priority: high
effort: L
rank: 0
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

## Closure note (2026-06-05)

Closed at 3/8 subtasks done (38%) by design — the V1-scoped three subtasks
(`worktree-service`, `worktree-write-routing`, `worktree-merge-queue`) all
shipped; the five remainder items above were consciously deferred to V2
rather than left as silent debt. Each deferred subtask exists as its own
ticket with `status: deferred` so the work is tracked, just not in flight.
The epic's "done at 38%" reading in `pyrite sw epics` is intentional, not a
data bug — surface here so future readers don't try to "finish the epic"
without revisiting the V2 prioritization first.
