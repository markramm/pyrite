---
id: playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap
title: 'Playwright e2e suite: non-deterministic failures, likely shared state + auth-config gap'
type: backlog_item
tags:
- bug
- ci
- testing
- e2e
importance: 5
status: proposed
priority: high
effort: M
rank: 0
---

## Problem

Investigating ci-make-green-and-load-bearing item 4 (triage Playwright e2e CI failures) surfaced a deeper, non-deterministic reliability problem beyond the two concrete bugs already fixed (see Related fixes below).

Running `npm run test:e2e` locally repeatedly produces a DIFFERENT set of failures each time -- not the same 18-20 tests, but overlapping sets that shift between runs. Examples observed in one session:

- Run 1 (before proxy fix): 18 failed, largely due to `/auth/config` and `/config/branding` 404ing against the Vite dev server (proxy missing those prefixes -- now fixed).
- Run 2 (after proxy fix): 20 failed -- a mostly different set, including tests that had been passing in Run 1 (`login page loads`, `register page loads`, several `collections.spec.ts` and `daily.spec.ts` tests).
- Run 3 (same code, no changes): 18 failed again, yet another different subset (`sidebar has navigation links` failed here but hadn't in Run 2; `Search Page loads` failed here but hadn't in Run 1).
- Running `e2e/app.spec.ts` alone, twice in a row, produced different results each time (3 failures once, 1 failure the next).

This is the same class of problem as `full-suite-only-flaky-tests-state-leak-across-test-files` (found earlier the same day on the *backend* suite) but on the frontend e2e suite instead. Suspected causes, not yet confirmed:

1. **Auth-state ambiguity**: several failing tests assume an auth-enabled backend (`/login` should show a Login page with title matching `/Login/`) but `playwright.config.ts` never configures `PYRITE_CONFIG`/auth settings for the launched backend, so it runs with whatever `load_config()` resolves to (likely auth disabled by default) -- `/login` then redirects away, breaking any test that assumes it renders. This looks structural, not flaky, and would explain `auth.spec.ts` failures consistently -- but they don't fail consistently, which suggests something else varies run to run.
2. **Shared KB/index state across the Playwright test run**: `entry-crud`, `qa`, `collections`, `timeline`, `search`, and `daily` specs all assert on the presence/absence of data ("shows entry list or empty state", "shows issues list or clean state", "No timeline events found"). If these tests run against a real KB directory that earlier tests in the same run mutate (create an entry, etc.), later assertions about "empty state" vs "has entries" become order-dependent -- classic shared-fixture flakiness.
3. Possibly a race in backend startup timing under `webServer` (uvicorn + vite booting in parallel) causing some page loads to hit the backend mid-startup on a loaded machine.

## Fix

1. Bisect: run the suite serially (`--workers=1`, already effectively serial for single-worker local runs) several times back to back, diffing which specific tests fail each time, to separate "genuinely flaky/order-dependent" from "deterministically broken given current fixture state."
2. Decide the intended auth-state contract for e2e tests explicitly (a dedicated test config with auth enabled + a seeded user, or confirm auth-disabled is correct and fix/quarantine the auth.spec.ts tests that assume otherwise) -- mirrors the same "what should this look like" question the backend flaky-test ticket raises, just for the web layer.
3. If shared KB/index state across specs is confirmed as a cause, give each e2e test file its own isolated KB fixture (or reset between files) rather than one shared backend instance for the whole suite run.

## Related fixes (already shipped, this investigation)

- Vite dev proxy was missing `/auth`, `/branding`, `/config` prefixes (only `/api` and `/health` were proxied to the backend) -- real product bug, any local-dev or e2e request to those paths 404'd against Vite itself. Fixed in vite.config.ts.
- `e2e/app.spec.ts`'s "loads and shows Pyrite branding" test used a `name: /Pyrite/` locator that matched both the sidebar logo link and a later-added footer link to pyrite.wiki (strict-mode violation, not a real app bug) -- fixed to scope by `href="/"`.
- Two backend tests (`test_collections_plugin.py`, `test_web_clipper.py`) walked `app.routes` directly, which broke against fastapi>=0.139's new `_IncludedRouter` internal representation. Fixed to use the stable `app.openapi()["paths"]` public API instead (see ci-make-green-and-load-bearing item 4 commit).

## Acceptance criteria

- `npm run test:e2e` run 3 times consecutively, same code, same machine: identical pass/fail set each time (currently: different every time).
- The auth-state contract for e2e is explicit and documented (either in playwright.config.ts comments or a fixture setup file), not implicit in whatever `load_config()` happens to resolve to.
- Zero e2e tests fail due to cross-spec shared state (verified by running each spec file in isolation vs. the full suite and confirming identical outcomes).
