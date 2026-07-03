---
id: fail-open-exception-sweep
type: backlog_item
title: "Fail-open exception sweep: ~10 broad excepts convert failure to false success at trust boundaries"
kind: tech_debt
status: proposed
priority: high
effort: S
created: "2026-07-03"
tags: [reliability, exceptions, audit-2026-07]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
- target: verify-after-write-on-the-index-path
  relation: related
  kb: pyrite
---

## Problem

The 2026-07-03 code audit categorized ~35 broad `except Exception`
sites: ~30% legitimate boundaries, ~50% logged-and-degraded (the
plugin registry's documented before-raises/after-swallows policy is
the good model), and ~20% truly swallowed — fail-open behavior at
exactly the seams where past field bugs emerged. Ranked:

1. `pyrite/server/mcp_server.py:159-160` — `except Exception: pass`
   in `__init__` around merging DB-registered KBs into config. If the
   SELECT fails, DB-registered KBs silently vanish from the MCP
   surface (the dual-registry class, again).
2. `pyrite/storage/index.py:888-891` (+ `:807`) — the invalid-status
   drift detector swallows validator errors and silently disables
   itself — the check built after the 75-entry status drift can turn
   itself off.
3. `pyrite/services/kb_service.py:1382` — any push exception is
   relabeled `push_error = "No remote configured"`, masking
   auth/network failures.
4. `pyrite/storage/index.py:310-311` — frontmatter `references`
   dropped silently on parse error (recall-bug class).
5. `pyrite/services/auth_service.py:663,729` — decryption failure
   silently treated as plaintext token (documented, but a
   security-relevant fail-open; at minimum log at warning).
6. `pyrite/plugins/registry.py:519-521` — KB-type compatibility check
   fails → `return True` (fail-open authorization).
7. Low-stakes unlogged: `storage/repository.py:256`,
   `document_manager.py:87-88`, alembic `002_collaboration_tables.py`
   (4× pass).

Also in-family, from the CLI consistency review:
`search_commands.py` rich-mode silently falls back to file search on
index errors (masks index corruption as degraded search), and
`qa_service.py:377` + `kb_service.py:106` log write failures at
`debug` level.

## Fix

Per site: narrow the except to expected types, log at warning+ with a
WHY comment, and convert fail-open to fail-closed (or an explicit
degraded-state result) where the site guards an invariant. Follow the
plugin-registry policy shape. Add ruff BLE001 (or a review-checklist
rule): no bare pass / fail-open without a log line and a WHY comment.

## Acceptance criteria

- Sites 1-6 fixed with a test each where feasible (fault-inject the
  swallowed exception, assert the failure is now visible).
- A lint or documented checklist rule prevents new fail-open sites.
