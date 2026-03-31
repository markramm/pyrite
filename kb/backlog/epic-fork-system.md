---
id: epic-fork-system
type: backlog_item
title: "Epic: Multi-User Git Collaboration System"
kind: epic
status: accepted
priority: high
effort: XL
tags: [web, collaboration, git]
links:
- target: web-ui-git-operations
  relation: has_subtask
  kb: pyrite
- target: per-user-fork-directories
  relation: has_subtask
  kb: pyrite
- target: fork-divergence-indicators
  relation: has_subtask
  kb: pyrite
- target: fork-conflict-resolution-ui
  relation: has_subtask
  kb: pyrite
- target: sync-conflict-resolution-ui
  relation: has_subtask
  kb: pyrite
---

## Problem

Hosting a shared Pyrite instance for multiple investigators requires the full git collaboration stack: basic git operations in the web UI, per-user fork directories for isolation, divergence detection, and conflict resolution. Without this, collaborators need CLI/external git tools, breaking the web-only workflow.

## Subtasks

1. [[web-ui-git-operations]] — Git commit, push, pull, and diff in the web UI
2. [[per-user-fork-directories]] — Server-side per-user fork directories
3. [[fork-divergence-indicators]] — UI indicators showing fork drift
4. [[sync-conflict-resolution-ui]] — Git sync conflict resolution UI
5. [[fork-conflict-resolution-ui]] — Visual conflict resolution when merging forks
