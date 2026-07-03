---
id: mypy-strict-ratchet-burn-down-pyrite-storage-errors
title: 'mypy strict ratchet: burn down pyrite/storage/ errors'
type: backlog_item
tags:
- tech-debt
- mypy
- ci
importance: 5
kind: task
status: proposed
priority: medium
effort: M
rank: 0
---

## Problem

ci-make-green-and-load-bearing item 6 added a `[[tool.mypy.overrides]]`
scaffold in pyproject.toml scoping `disallow_untyped_defs = true` to
`pyrite.storage.*` — but did not fix the existing errors that flag
triggers. CI's mypy step stays `continue-on-error: true` and uses a
plain `mypy pyrite/ --ignore-missing-imports` invocation (no
`--disallow-untyped-defs`), so this override is not yet load-bearing
anywhere — it's a documented target, not an enforced gate.

Baseline (2026-07-03, `mypy pyrite/storage/ --ignore-missing-imports
--follow-imports=silent --disallow-untyped-defs`): **281 errors, 15
files**. Category breakdown (from a full `--strict` pass, 313 errors/16
files): 113 attr-defined, 64 no-any-return, 34 no-untyped-def, 26
arg-type, 25 assignment, 15 union-attr, 2 index, 1 operator, 1 misc.

The storage layer is where dual-registry KB drift and silent
index-desync bugs have concentrated this session (see
merge_registered_kbs consolidation, content-hash staleness detection) —
that history is why this layer was picked over a repo-wide ratchet.

## Fix

1. Burn down errors incrementally, file-by-file (start with the
   smallest/highest-value files, e.g. document_manager.py's single
   operator error, rather than index.py's ~113 attr-defined bulk).
2. Once `pyrite/storage/*` passes `--disallow-untyped-defs` cleanly,
   flip CI's mypy step to non-`continue-on-error` scoped to that
   override (or add a dedicated `mypy pyrite/storage/
   --disallow-untyped-defs` CI step that DOES gate the build).
3. Consider whether `no-any-return` (64 errors) and `attr-defined` (113
   errors, likely SQLAlchemy Row/Result typing) are worth a second
   ratchet phase, or need targeted type: ignore with a linked ticket
   comment instead of a blanket suppression.

## Acceptance criteria

- `mypy pyrite/storage/ --ignore-missing-imports --follow-imports=silent
  --disallow-untyped-defs` returns 0 errors.
- CI actually gates on this (not continue-on-error) for the storage
  scope.

