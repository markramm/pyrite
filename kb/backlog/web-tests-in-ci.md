---
id: web-tests-in-ci
type: backlog_item
title: "Run frontend unit + Playwright E2E tests in CI"
kind: improvement
status: proposed
priority: high
effort: S
tags: [ci, testing, frontend, dx]
---

## Problem

`.github/workflows/ci.yml` runs `pytest` against `pyrite/` but does not run
the frontend test suite. Today:

- `web/` has 35 unit tests (`*.test.ts` / `*.spec.ts` under `src/`)
- `web/e2e/` has 11 Playwright E2E tests (auth, entry-crud, daily, search,
  collections, qa, graph, timeline, …)

None of these run on push or PR. The `playwright-integration-tests` ticket
that "shipped" landed the test files but not the CI wiring — `git grep -l
playwright .github/` returns nothing.

Result: frontend regressions only get caught locally if a contributor
remembers to run `cd web && npm run test:unit && npm run test:e2e`.
Realistically, they don't.

## Solution

1. Add a `frontend` job to `.github/workflows/ci.yml`:
   - `actions/setup-node@v4` with the version pinned in `web/.nvmrc` or
     `package.json` `"engines"`.
   - `npm ci` in `web/`.
   - `npm run check` (svelte-check / tsc).
   - `npm run test:unit`.
   - `npm run build` to catch build-time regressions.
2. Add an `e2e` job, separate from `frontend` so unit failures don't block
   the e2e signal:
   - Spin up the backend (`pytest` already proves backend works; here we
     need a running server — use a `pyrite serve` invocation against a
     seeded temp KB, or the existing playwright fixture).
   - Install Playwright browsers (`npx playwright install --with-deps`).
   - `npm run test:e2e`.
3. Cache `node_modules` and the Playwright browser binaries to keep CI fast.
4. Block PRs on the new jobs.

## Acceptance criteria

- `.github/workflows/ci.yml` includes frontend unit + build + e2e jobs.
- Failing unit or e2e test fails the PR check.
- CI completes within an acceptable window (target: < 10 min wall time).
- README badge updated if applicable.

## Related

- `mypy strict enforcement` — companion ticket for backend type safety
- `playwright-integration-tests` (already done — that landed the tests; this
  finishes the CI side)
