---
id: ci-make-green-and-load-bearing
type: backlog_item
title: "Make CI green and load-bearing: 100/100 recent runs failed; pre-commit configured but not installed"
kind: bug
status: proposed
priority: high
effort: M
created: "2026-07-03"
tags: [ci, testing, reliability, audit-2026-07]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
---

## Problem

The 2026-07-03 audit found CI has NEVER been green in visible history:
100 of the last 100 runs (2026-04-06 → 2026-06-26) concluded `failure`.
Latest run: the unit-test matrix job died at ruff in 18 seconds — the
Python suite never executed; `test-optional-deps` failed in pytest;
Playwright e2e failed; only frontend passed. Meanwhile:

- `ruff check pyrite/` exits 0 LOCALLY — the CI failure is likely a
  ruff version or scope mismatch (CI may lint tests/ or pin a
  different ruff), i.e. probably cheap to fix.
- `.pre-commit-config.yaml` defines ruff, import-cycle check, schema
  validate, and a pytest quick check — but `.git/hooks/` contains only
  `.sample` files. The hooks have never run.
- No postgres service container; `PYRITE_TEST_PG_URL` never set, so
  all 71 postgres conformance params skip in CI. The postgres
  edge-endpoint data loss (6c49e59 "was silently dropping data")
  shipped through exactly this gap.
- mypy is `continue-on-error: true`; coverage measured, gates nothing.

A permanently-red CI is worse than none: it trains humans and agents
to ignore the signal, so a genuinely new failure is invisible. The
actual merge gate today is whatever gets run locally.

## Fix

1. Diagnose and fix the CI ruff failure (align version/scope with
   local config); get the matrix job to actually run pytest.
2. `pre-commit install` on dev machines + document in CLAUDE.md; the
   quick-check hook becomes the real local gate.
3. Add a postgres service container to CI and set
   `PYRITE_TEST_PG_URL` so the conformance suite tests both backends.
4. Triage `test-optional-deps` and Playwright failures: fix or
   quarantine with tickets — zero tolerated-red jobs.
5. Optional ratchets once green: `fail_under` on coverage; a check
   that `fix:`-prefixed commits touch `tests/` (mechanizes Iron Law 1
   — the 40e7a39 fix shipped with zero test lines).
6. Ratchet mypy strict on `pyrite/storage/` only (280 sampled errors
   concentrate there — the layer that produced the field bugs).

## Acceptance criteria

- CI green on dev HEAD, and red CI blocks (or at minimum pages)
  rather than being ambient.
- Postgres conformance runs in CI (0 skips for the postgres param).
- Pre-commit hooks installed and passing locally.
