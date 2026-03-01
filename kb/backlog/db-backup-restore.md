---
id: db-backup-restore
title: "Database Backup and Restore"
type: backlog_item
tags:
- feature
- infrastructure
- operations
- database
kind: feature
priority: medium
effort: S
status: planned
links:
- postgres-storage-backend
- demo-site-deployment
- roadmap
---

## Problem

Git backs up the knowledge files, but the SQLite database contains state that doesn't rebuild from `pyrite index sync`: settings, user preferences, starred entries, collection configuration, and other user-generated data. Losing the database means losing personalization and configuration.

Vectors and the FTS index *do* rebuild from `index sync` — those don't need backup.

## Solution

```bash
# Backup non-rebuildable tables
pyrite db backup --output backup-2026-03-01.json

# Restore from backup
pyrite db restore --input backup-2026-03-01.json

# List what's in a backup
pyrite db backup --dry-run
```

### What Gets Backed Up

- Settings (user preferences, AI provider config)
- Starred entries
- API keys (hashed)
- Collection user state (view preferences, sort orders)
- Any future application-layer state

### What Does NOT Get Backed Up (rebuildable)

- Entry index (rebuilt by `pyrite index sync`)
- FTS index (rebuilt by indexing)
- Embedding vectors (rebuilt by embedding pipeline)
- Block table (rebuilt by indexing)

### Format

JSON export for portability. Works across SQLite and Postgres backends. Includes schema version for forward compatibility.

## Prerequisites

- None — straightforward export/import of specific tables

## Success Criteria

- `pyrite db backup` exports all non-rebuildable state
- `pyrite db restore` imports cleanly
- Round-trip preserves all data
- Works on both SQLite and Postgres backends
- Documented in operations runbook

## Launch Context

Nice-to-have for 0.8. Becomes important for demo site (periodic reset to clean state) and any production deployment.
