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

## Decision (2026-07-03): ADR-0029 governs this ticket

The design discussion concluded and is recorded in [[adr-0029]]
(Libraries, KB Lifecycles, and Runtime State). The 0.25 scope of
THIS ticket, per the ADR's phasing:

1. Finish the `all_kbs()` sweep (the Problem list above), regression
   test per site.
2. Consolidate to ONE YAML: the merged file becomes a valid library
   file named `default` (`library:` header, full KB list, `db:`
   path); `~/kb/config.yaml` migrated in and retired; `~/.pyrite/`
   owns the registry; stale test registrations dropped during
   migration.
3. `pyrite kb create` / `kb add` WRITE the library YAML (ruamel
   round-trip, file lock + atomic rename); the DB `kb` table is
   demoted to a derived cache rebuilt from the file at load, with
   read-back verification.
4. Load-time validation: a malformed library file fails with a good
   error, never silent divergence.

Library switching, per-library DBs, readonly mounts, claim leases,
and ephemeral leasing are 0.26 (see the ADR) — do NOT implement here.

## Notes

Sibling of [[verify-after-write-on-the-index-path]]; together they retire the derived-state-synchronization bug class.

The same dual-registry class also exists one level up in the primary deployment: `~/kb/config.yaml` and `~/.pyrite/config.yaml` disagree on paths for ~25 KBs (biography KBs point at `pyrite-kb-demo/` in one and `tcp-kb-internal/` in the other; `~/.pyrite` still registers stale `/private/tmp/test-release-kb` and `test-tasks`). The ADR resolves this via the one-file consolidation above. This also closes the registry-ADR item in [[file-missing-adrs-for-session-arc-decisions]].
