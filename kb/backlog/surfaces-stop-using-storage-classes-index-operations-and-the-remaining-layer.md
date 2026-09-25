---
id: surfaces-stop-using-storage-classes-index-operations-and-the-remaining-layer
title: 'Surfaces stop using storage classes: index operations and the remaining layer-ratchet entries behind services'
type: backlog_item
tags:
- architecture
- programmatic-validation
importance: 5
kind: improvement
status: proposed
priority: medium
effort: M
rank: 0
---

Follow-up to #380. tests/test_layer_boundaries.py counts every place a surface (pyrite/server, pyrite/cli, pyrite/ui, admin_cli, read_cli) imports or uses a pyrite.storage class, or reaches a DB handle, and its ALLOWLIST can only shrink. What #380 left on it that no other ticket owns:

- IndexManager driven directly by the CLI and pyrite-admin (index build/sync/stats/health/embed/reconcile, init, kb validate, schema migrate, search's empty-index and staleness checks) and by the REST /stats and /index/sync handlers. An IndexService (or KBService methods) would own these.
- KBRepository / DocumentManager used by the CLI (search --files, index reconcile, schema migrate).
- Handlers handing a DB to a helper: admin.py sync_index (index_mgr.db into _drain_embed_queue and SiteCacheService), collections.py preview_collection_query (svc.db into evaluate_query), the qa CLI commands building QAService/URLChecker from ctx.db.
- db.vec_available read by the index CLI commands.
- pyrite db backup/restore using sqlite3 directly.
- server/worktree_resolver.py: a service living under server/ (builds WorktreeDB overlays); move it to services/.

## Acceptance
- [ ] Each moved reach removes its ALLOWLIST entry and lowers ALLOWLIST_SIZE in tests/test_layer_boundaries.py.
- [ ] No behaviour change: the CLI JSON outputs and the REST responses are unchanged.
