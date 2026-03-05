---
id: plugin-hook-atomicity
type: backlog_item
title: "Make plugin hook execution atomic with DB transactions"
kind: improvement
status: completed
milestone: "0.17"
priority: high
effort: S
tags: [plugins, storage, reliability]
links:
- plugin-system
- database-transaction-management
---

# Make plugin hook execution atomic with DB transactions

## Problem

If a `before_save` plugin hook raises an exception, the entry may be partially saved — the hook failure doesn't trigger a transaction rollback. This breaks the expectation that hooks can veto writes.

## Solution

Wrap the save + hook execution in a single database transaction:

1. Begin transaction
2. Run `before_save` hooks — if any raise, rollback and propagate error
3. Persist entry
4. Run `after_save` hooks — if any raise, log warning but don't rollback (entry is committed)
5. Commit

Also add explicit hook ordering (pre-db, db, post-db) so plugin authors know when their hook runs relative to persistence.

## Files

- `pyrite/services/kb_service.py` — save/update entry flow
- `pyrite/plugins/registry.py` — hook dispatch
- `pyrite/plugins/protocol.py` — hook ordering documentation
