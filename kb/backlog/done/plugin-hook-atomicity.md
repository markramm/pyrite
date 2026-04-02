---
id: plugin-hook-atomicity
title: "Make plugin hook execution atomic with DB transactions"
type: backlog_item
tags: [plugins, storage, reliability]
links:
- target: plugin-system
  relation: related
- target: database-transaction-management
  relation: related
kind: improvement
status: done
priority: high
effort: S
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
