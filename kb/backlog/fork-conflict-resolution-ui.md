---
id: fork-conflict-resolution-ui
title: "Fork Conflict Resolution UI and Storage Optimization"
type: backlog_item
tags:
- feature
- web-ui
- collaboration
- git
kind: feature
priority: low
effort: L
status: deferred
links:
- adr-0018
- fork-divergence-indicators
- per-user-fork-directories
- target: epic-fork-system
  relation: subtask_of
  kb: pyrite
---

## Problem

When a fork sync encounters merge conflicts, users currently have no way to resolve them from the web UI. ADR-0018 Phase 4 covers conflict resolution and storage optimization.

## Solution

### Conflict Resolution

- Detect merge conflicts during `sync()` and surface them in the UI
- Side-by-side diff editor showing "yours" vs "theirs" with accept/reject controls per hunk
- "Discard my changes" option: reset fork to upstream (`git reset --hard origin/main`)
- "Keep my version" option: force-keep fork version and mark conflict resolved

### Storage Optimization

- Shared git objects between forks on the same filesystem (hardlinks)
- Shallow clone depth tuning (currently `--depth=1`)
- Fork deduplication: detect when multiple users fork the same repo and share read-only objects
- Metrics: track disk usage per user and per fork

## Prerequisites

- Per-user fork directories
- Fork divergence detection
