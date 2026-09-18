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

## Update 2026-09-16: the job is now NON-BLOCKING, and this ticket owns restoring it

`continue-on-error: true` was added to the `e2e` job in `.github/workflows/ci.yml`.

Rationale: three other CI-config bugs were fixed the same day (below), which
should take `test` and `test-optional-deps` green -- but while `e2e` blocks on a
suite that fails differently every run, the overall CI run stays red regardless,
and a permanently-red CI is the exact signal-destroying condition
[[ci-make-green-and-load-bearing]] was written to end.

**This ticket now owns flipping that back.** The `continue-on-error` line carries
a REVERT comment pointing here. Until it is removed, the frontend has NO enforced
gate in CI -- which raises this ticket's stakes rather than lowering them: it is
now the only thing standing between the web UI and an untested merge path, on the
surface the shared-instance pilot peers actually use
([[epic-shared-instance-readiness]] workstream 4).

### Fresh evidence from CI runners (2026-09-16)

Three fork-PR runs plus the dev baseline all failed `e2e`, confirming the
diagnosis above from clean runner environments rather than only local runs:

- `locator('text=New Entry') resolved to 2 elements` (3 occurrences)
- `locator('text=No entries found').or(locator('[href^="/entries/"]').first()) resolved to 2 elements` (3 occurrences)
- `expect(page).toHaveTitle(expected) failed`
- multiple `expect(locator).toBeVisible() failed -- element(s) not found`

The strict-mode violations are the same class as the already-fixed `app.spec.ts`
logo/footer collision: locators matched against visible **text** rather than a
stable role / `href` / test-id, so any later-added element carrying the same
string silently breaks a previously-passing test. That is a suite-wide
locator-strategy problem, not three isolated bugs -- a sweep for `text=`-based
locators belongs in the fix.

### Related CI-config bugs fixed the same day (all separate from this ticket)

These were the *other* reasons CI was red; none are e2e's fault, and fixing them
is what leaves this ticket as the remaining blocker:

1. The `test` matrix installed `.[dev,postgres]`, but `dev` is test tooling only
   (pytest/mypy/ruff) -- it pulls neither `typer`/`rich` (`cli`) nor
   `bcrypt`/`fastapi` (`server`), and the core `dependencies` block doesn't
   either. 70 test modules failed at COLLECTION with `ModuleNotFoundError` on all
   three Python versions while pip still exited 0. Now `.[all,postgres]`.
2. `-W error::DeprecationWarning` was unscoped, promoting third-party
   deprecations (anyio's `BlockingPortal` alias) to hard errors -- any upstream
   release could turn CI red with no pyrite change. Now scoped to `pyrite` and
   `tests`.
3. `tests/test_worktree_service.py` ran bare `git init`, which yields `master` on
   GitHub runners while `GitService` hardcodes `main` -- six CI-only failures
   (`pathspec 'main' did not match`). Now `git init --initial-branch=main`.

## Acceptance criteria

- `npm run test:e2e` run 3 times consecutively, same code, same machine: identical pass/fail set each time (currently: different every time).
- The auth-state contract for e2e is explicit and documented (either in playwright.config.ts comments or a fixture setup file), not implicit in whatever `load_config()` happens to resolve to.
- Zero e2e tests fail due to cross-spec shared state (verified by running each spec file in isolation vs. the full suite and confirming identical outcomes).
- No spec identifies an element by bare visible text where a role, `href`, or `data-testid` would be stable (the strict-mode-violation class above).
- **`continue-on-error: true` is removed from the `e2e` job in `ci.yml`** and a full CI run passes with e2e blocking again. This ticket is not done while that line survives.

## Analysis 2026-09-18 (conductor): why the suite fails differently every run

Evidence: eight consecutive failed `e2e` jobs on CI (2026-09-17/18), the ticket's
own 2026-09-16 runner evidence, and the specs.

**1. The suite has no test-data contract; it assumes a world.**
`playwright.config.ts` starts `uvicorn pyrite.server.api:app` with no
`PYRITE_*` environment and `reuseExistingServer: !CI`. Locally that is Mark's
real config (47 KBs, real daily notes, other sessions writing); on a CI runner
it is an empty home: zero KBs, zero entries. Every spec then asserts on data:
the Dashboard heading and stat cards (the page renders its zero state with no
KBs), "shows edit button when daily note exists", "shows entry", collections
headings. The failure signature confirms it: the same specs fail on every CI
run at 5.1–5.6 s, which is the default `expect` timeout — the page loaded, the
element never existed. Locally the failing set *shifts* because the world
shifts (specs create daily notes in a real KB; the daily GET itself creates
today's note — `web-daily-notes-view-side-effect`). "Non-deterministic" is the
wrong name; the suite is deterministic on its input, and its input is
undefined.

**2. Locators keyed on visible text.** `text=New Entry`, `text=Daily Notes`,
`locator('h1').first()` — every later-added element with the same words is a
strict-mode violation (the runner evidence: "resolved to 2 elements" ×6). The
logo/footer fix in `app.spec.ts` was one instance of a class.

**3. Environment ambiguity.** Auth state is unspecified (specs for /login and
/register assume auth pages exist); the backend `webServer` has a 15 s timeout
that a cold runner importing torch can exceed; nothing pins `PYRITE_AUTO_EMBED`.

None of the three is fixed by retries, which is why `retries: 2` only made the
job three times slower.

## Plan: foundation first, then mechanical fan-out

**Package A — the deterministic world (one worker, Opus).**
- `web/e2e/global-setup.ts`: create a temp `PYRITE_DATA_DIR`/`PYRITE_CONFIG_DIR`,
  write a config with auth **disabled** explicitly, `PYRITE_AUTO_EMBED=0`,
  seed one KB `e2e` with a fixed set of entries (people, events, notes, a
  collection, a daily note for a fixed date) via `pyrite init` + `pyrite
  create`; export the seed as constants in `web/e2e/fixtures.ts`.
- `playwright.config.ts`: backend `webServer` gets that `env`;
  `reuseExistingServer: false` always (a local run must never touch real KBs);
  backend timeout 60 s; `retries: 0` (a flake must be visible, not absorbed).
- Specs that write get unique titles (`uniqueTitle()` helper) or their own KB.
- Fix or isolate the daily-GET side effect for the seeded world (it is also a
  read-tier violation: `web-daily-notes-view-side-effect`).
- Prove it: 5 consecutive green local runs, then 5 on CI by dispatch.
- Record: this analysis into the ticket; ADR-0032 §3a "Playwright on main".

**Packages B–G — one Sonnet worker per group, disjoint footprints, after A.**
Rewrite each spec against the seeded world: assertions on seeded data; roles,
`href`s, or `data-testid` instead of text; add `data-testid` to the Svelte
component only where no role exists. Each package = spec file(s) + the
page component(s) they touch, so no two packages share a file:
  B: app.spec + settings.spec (layout, dashboard, settings pages)
  C: auth.spec (login/register — decide: skip when auth disabled, or a second
     project with auth enabled and a seeded user; A decides, B implements)
  D: entry-crud.spec + entry-features.spec (entries pages)
  E: collections.spec + daily.spec
  F: graph.spec + timeline.spec
  G: qa.spec + search.spec
Acceptance per package: its specs pass 5× in a row against A's world; zero
`text=` locators; no `.first()` to dodge a strict-mode violation.

**Package H — wire it in (Sonnet, after B–G).** `e2e` job runs on pushes to
`main` (the value chain's depth layer) with `retries: 0`; the report artifact
stays; the `continue-on-error` line goes; `tests/test_dev_process_config.py`
pinned. On `dev` pushes only after ten consecutive greens on `main`.

Sequencing: A alone (it changes the config every package depends on); B–G in
parallel from the merged A; H last. Three conductor ticks.
