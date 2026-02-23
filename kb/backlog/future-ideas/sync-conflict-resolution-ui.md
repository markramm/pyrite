---
type: backlog_item
title: "Git Sync Conflict Resolution UI"
kind: feature
status: proposed
priority: low
effort: L
tags: [web, git, ux]
---

Visual conflict resolution when git sync encounters merge conflicts:

- Detect conflicts after `pyrite sync` / git pull
- Show conflicting entries in web UI with side-by-side diff
- Three-way merge: mine / theirs / merged result
- Accept left, accept right, or manual edit
- Resolve and commit from the UI

Unique to git-native tools. Currently conflicts require CLI git knowledge, which is a barrier for non-technical users. This makes Pyrite's git-native approach accessible.
