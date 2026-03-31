---
id: epic-fork-system
type: backlog_item
title: "Epic: Per-User Fork System for Multi-User Editing"
kind: epic
status: proposed
priority: medium
effort: XL
tags: [web, collaboration, git]
links:
- target: per-user-fork-directories
  relation: has_subtask
  kb: pyrite
- target: fork-divergence-indicators
  relation: has_subtask
  kb: pyrite
- target: fork-conflict-resolution-ui
  relation: has_subtask
  kb: pyrite
---

## Problem

Multi-user editing on a shared Pyrite instance requires per-user fork directories so users can work independently without conflicting writes. This epic groups the three features needed: fork directory isolation, divergence detection, and conflict resolution.

## Subtasks

1. [[per-user-fork-directories]] — Server-side per-user fork directories
2. [[fork-divergence-indicators]] — UI indicators showing fork drift
3. [[fork-conflict-resolution-ui]] — Visual conflict resolution when merging forks
