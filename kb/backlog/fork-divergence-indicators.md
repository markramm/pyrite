---
id: fork-divergence-indicators
title: "Fork Divergence Detection and UI Indicators"
type: backlog_item
tags:
- feature
- web-ui
- collaboration
- git
kind: feature
priority: medium
effort: M
status: proposed
links:
- adr-0018
- web-kb-management
- target: epic-fork-system
  relation: subtask_of
  kb: pyrite
---

## Problem

When a user's fork diverges from upstream, the web UI gives no indication. Users may unknowingly edit stale content or miss upstream updates. ADR-0018 specifies divergence indicators but they haven't been built.

## Solution

### Backend

- Add `get_fork_divergence(repo_name)` to `RepoService` — compares fork HEAD vs upstream HEAD, returns counts of entries ahead/behind/diverged
- Add `GET /api/repos/{name}/divergence` endpoint returning `{ahead: N, behind: N, diverged_entries: [...]}`
- Per-entry comparison: diff fork version vs upstream version for a given entry

### Web UI Indicators

- **Entry list**: Badge showing "N entries differ from upstream" on KB cards
- **Entry view**: Banner when user's version differs: "Your version differs from upstream. [View upstream] [Submit PR]"
- **KB detail page**: Sync status indicator (up-to-date, behind, ahead, diverged)
- **Header/sidebar**: Fork sync state icon

### Diff View

- Side-by-side comparison of user's entry vs upstream version
- Accessible from the divergence banner on entry pages

## Prerequisites

- Per-user fork directories (or current shared fork model)
- GitHub integration (completed)
