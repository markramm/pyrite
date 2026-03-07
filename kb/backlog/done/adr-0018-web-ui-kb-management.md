---
id: adr-0018-web-ui-kb-management-backlog
type: backlog_item
title: "ADR-0018: Web UI KB Management via Git Forks"
kind: feature
status: completed
milestone: "0.18"
priority: medium
effort: XS
tags: [architecture, web-ui, adr]
links:
  - target: "adr-0018"
    relation: "implements"
---

# ADR-0018: Web UI KB Management via Git Forks

## Problem

No design document existed for how the web UI should handle multi-user KB management — per-user isolation, upstream syncing, and conflict resolution.

## Solution

Wrote ADR-0018 documenting a git fork-based architecture:
- Per-user shallow forks for isolation
- PR-based merge workflow back to upstream
- UI divergence indicators showing where user content differs from upstream
- Leverages existing RepoService and GitService infrastructure

## Files

- `kb/adrs/0018-web-ui-kb-management.md`
