---
id: add-ruff-ble001-blind-except-lint-gate-for-fail-open-prevention
title: Add ruff BLE001 (blind-except) lint gate for fail-open prevention
type: backlog_item
tags:
- tech-debt
- linting
- reliability
importance: 5
kind: task
status: proposed
priority: medium
effort: M
rank: 0
---

## Problem

fail-open-exception-sweep's acceptance criteria calls for "a lint or
documented checklist rule that prevents new fail-open sites" but no
such gate exists yet. Ruff's `BLE001` (blind-except) is the natural
mechanical check — it flags any `except Exception:` that doesn't
narrow to a specific type.

Checked feasibility (2026-07-03): `ruff check pyrite/ --select BLE001`
finds **153 pre-existing violations** across the codebase (top
concentrations: storage/index.py 13, plugins/registry.py 12,
services/kb_service.py 10, server/endpoints/admin.py 10,
github_auth.py 8). Most of these are legitimate — narrowing every
`except Exception` to specific types is a large, cross-cutting change,
and this sweep's own audit found ~30% of broad excepts are correct as
written (defensive boundaries at genuine unknowns). Turning the rule
on today would either fail CI immediately or require blanket
per-file-ignores that defeat the purpose.

## Fix

Same ratchet shape as the mypy strict-mode ratchet on
`pyrite/storage/` (see
[[mypy-strict-ratchet-burn-down-pyrite-storage-errors]]): don't
enable repo-wide. Options, in order of preference:

1. Add `BLE001` to `[tool.ruff.lint].select` but suppress via
   `per-file-ignores` for all currently-violating files, so ONLY new
   code (new files, or files that get fully cleaned up) is gated.
   Burn down file-by-file, shrinking the ignore list over time.
2. A pre-commit or CI check scoped to the diff only (`ruff check
   --select BLE001` on changed lines, similar to `--changed` in
   `pyrite schema validate`) — catches new fail-open sites without
   touching existing ones at all.
3. Document the rule as a code-review checklist item (weakest, but
   zero setup cost) if neither mechanical option is worth the
   investment right now.

## Acceptance criteria

- New `except Exception` sites without narrowing or a log+WHY comment
  are caught before merge (CI or pre-commit), OR the checklist
  documentation exists in CLAUDE.md / pyrite-dev skill as an interim
  measure.
- Closes the last open item of fail-open-exception-sweep.

