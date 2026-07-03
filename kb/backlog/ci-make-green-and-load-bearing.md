---
id: ci-make-green-and-load-bearing
title: "Make CI green and load-bearing: 100/100 recent runs failed; pre-commit configured but not installed"
type: backlog_item
tags: [ci, testing, reliability, audit-2026-07]
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
importance: 5
kind: bug
status: proposed
priority: high
effort: M
rank: 0
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

## Progress

- [x] **Item 1 — CI ruff failure diagnosed and fixed** (86e4ff3,
  2026-07-03) — not a version/scope mismatch as hypothesized
  (`ruff>=0.15.0,<0.16` pin matches local 0.15.2 exactly). CI's lint
  step runs both `ruff check` (already clean) and `ruff format
  --check` (was failing: 82 files had drifted out of formatting
  compliance, root-caused to item 2 below -- pre-commit's ruff-format
  hook never ran on any commit). Applied `ruff format pyrite/
  tests/`; diff confirmed whitespace/style-only; full suite re-run
  clean (3018 passed) after the reformat.
- [x] **Item 2 — pre-commit install + hook fixes** (74a2cb1,
  2026-07-03) — `pre-commit` was never a declared dependency (no
  pyproject.toml entry) -- root cause of item 1's drift. Added
  `pre-commit>=3.6.0` to dev extras; unset a redundant local
  `core.hooksPath` override that blocked installation; installed
  hooks. Fixed the `pyrite-schema-validate` hook itself (never
  successfully ran before -- `python -m pyrite` fails, pyrite/ has no
  `__main__.py`; now calls the `pyrite` console script directly), and
  a scoping bug that fix exposed (`--changed` validated non-KB
  markdown as KB entries; added KB-path filtering, two new tests).
  Documented setup + a flaky-test caveat in CLAUDE.md.
- [x] **Item 3 — postgres service container in CI** (fc241bf,
  2026-07-03) — three compounding gaps, all fixed: no service
  container; `PYRITE_TEST_PG_URL` never set; the `test` matrix job
  never installed the `postgres` extra (psycopg2-binary, pgvector) at
  all, so even a live DB would have skipped via the driver-import
  fallback in `tests/backends/conftest.py`. Added a `postgres`
  service using `pgvector/pgvector:pg16` (not plain `postgres:*` --
  `ensure_schema()` runs `CREATE EXTENSION vector`, which needs the
  extension installed in the image). `test-optional-deps` left alone;
  `test` now covers postgres conformance across all 3 Python
  versions. Verified against the real image locally (Docker, not just
  YAML inspection): `tests/backends/` -- 138 passed (67 conformance x2
  backends + 4 exec-error + sqlite half). Full suite with
  `PYRITE_TEST_PG_URL` set: 3086 passed, 1 skipped (up from 3019 with
  postgres disabled), no cross-backend interaction failures, no flaky-
  test recurrence.
- [x] **Item 4 — test-optional-deps and Playwright triaged, both
  fixed where fixable** (f9ad329, 2026-07-03) — replicated
  `test-optional-deps` exactly (fresh venv, `.[all]` + all extensions
  in dev mode; my main dev venv had accumulated extra packages and
  didn't reproduce the failure). Root cause: `fastapi` has no upper
  version bound, fresh install got 0.139.0 (vs 0.132.0 locally), which
  changed `app.routes`' internal shape (`_IncludedRouter` wrapper
  objects without a `.path` attribute, nested routes not reachable via
  a plain `.routes` walk). Two tests
  (`test_collections_plugin.py`, `test_web_clipper.py`) assumed the
  old shape; fixed to use `app.openapi()["paths"]` instead (FastAPI's
  stable public API, correct on both versions). Left `fastapi`
  unbounded -- the fix itself is now version-independent.
  Frontend (`npm run check`, `test:unit`, `build`) all passed clean
  locally, nothing to fix. Playwright e2e: found and fixed two real
  bugs -- the Vite dev proxy was missing `/auth`, `/branding`,
  `/config` (only `/api`/`/health` forwarded to the backend, so those
  paths 404'd against Vite itself; a real local-dev bug, not e2e-only)
  and one strict-mode-violation locator in `app.spec.ts` (a later-added
  footer link started matching the same name pattern as the nav logo
  link). Both verified fixed and stable on repeated runs.
  **Surfaced but NOT fixed here:** the e2e suite produces a different
  set of failures on every run (18, then 20, then 18 again -- not the
  same tests), the same class of problem as the backend flaky-test
  finding below, just on the frontend. Filed separately as
  [[playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap]]
  (high, M) rather than expanding this investigation into an e2e
  auth-fixture / test-isolation redesign.
- [ ] Item 5 — optional ratchets (coverage `fail_under`, `fix:`-commit
  test-touch check)
- [ ] Item 6 — mypy strict ratchet on `pyrite/storage/`

**Related finding, filed separately:** fixing item 2 (the pytest-check
hook now actually runs the full suite with `-x`) surfaced three
full-suite-only flaky tests today (`test_index_worker.py`,
`test_review_flow_e2e.py` -- now removed as an unrelated product
decision, and `test_worktree_service.py`), none reproducible in
isolation, none related to the diffs that triggered them. This is the
same "permanently-red trains people to ignore the signal" problem
this ticket's own problem statement describes, just one layer down at
the local pre-commit hook instead of CI. Filed as
[[full-suite-only-flaky-tests-state-leak-across-test-files]] (high,
M) -- likely blocks fully closing this ticket's acceptance criteria,
since a red-on-flake `-x` hook isn't a trustworthy local gate either.

## Acceptance criteria

- CI green on dev HEAD, and red CI blocks (or at minimum pages)
  rather than being ambient.
- Postgres conformance runs in CI (0 skips for the postgres param).
- Pre-commit hooks installed and passing locally.



