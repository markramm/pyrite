---
id: collapse-kb-registry-to-one-source-of-truth
title: Collapse KB registry to one source of truth (finish knowledge_bases -> all_kbs() sweep)
type: backlog_item
tags:
- tech-debt
- config
- index
importance: 5
kind: tech_debt
status: proposed
priority: medium
effort: M
rank: 0
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
---

## Problem

KBs live in two registries: config.yaml (`config.knowledge_bases`) and the DB `kb` table (`pyrite kb add`, reachable only via `get_kb()`/`all_kbs()` through `_db_kb_cache`). Every loop over `config.knowledge_bases` silently skips DB-registered KBs — the bug class `all_kbs()`'s own docstring warns about.

The index/MCP sites were fixed (index.py get_index_stats/check_staleness/check_health x3, mcp_server.py _list_edge_types — see tests/test_index_covers_db_registered_kbs.py). Remaining direct-iteration sites to audit and migrate (some may be intentionally config-only, e.g. seeding and worktree patching):

- pyrite/config.py:843
- pyrite/ui/data.py:57, 166
- pyrite/cli/schema_commands.py:468, 479
- pyrite/cli/search_commands.py:105 (error-message KB list)
- pyrite/services/sitemap_service.py:43
- pyrite/services/kb_registry_service.py:34
- pyrite/services/site_cache.py:67
- pyrite/services/ephemeral_service.py:56, 74, 89
- pyrite/services/qa_service.py:157
- pyrite/services/kb_service.py:125, 172

## Proposal

1. Audit each site: config-only semantics intentional, or silent-skip bug?
2. Migrate bug sites to `all_kbs()` with a regression test each (fixture pattern in tests/test_index_covers_db_registered_kbs.py).
3. Longer term: make `knowledge_bases` private or rename, so enumeration goes through `all_kbs()` by default and config-only access is the explicit opt-in.

## Notes

Sibling of [[verify-after-write-on-the-index-path]]; together they retire the derived-state-synchronization bug class.

The same dual-registry class also exists one level up in the primary deployment: `~/kb/config.yaml` and `~/.pyrite/config.yaml` disagree on paths for ~25 KBs (biography KBs point at `pyrite-kb-demo/` in one and `tcp-kb-internal/` in the other; `~/.pyrite` still registers stale `/private/tmp/test-release-kb` and `test-tasks`). Whatever single-source design lands here should either make that drift structurally impossible or auto-reconcile it with a warning. Decision deserves an ADR — see [[file-missing-adrs-for-session-arc-decisions]] (index-health drift checks).
