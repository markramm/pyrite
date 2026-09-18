---
body: "## Problem\n\nInvestigating ci-make-green-and-load-bearing item 4 (triage Playwright e2e CI failures) surfaced a deeper, non-deterministic reliability problem beyond the two concrete bugs already fixed (see Related fixes below).\n\nRunning `npm run test:e2e` locally repeatedly produces a DIFFERENT set of failures each time -- not the same 18-20 tests, but overlapping sets that shift between runs. Examples observed in one session:\n\n- Run 1 (before proxy fix): 18 failed, largely due to `/auth/config` and `/config/branding` 404ing against the Vite dev server (proxy missing those prefixes -- now fixed).\n- Run 2 (after proxy fix): 20 failed -- a mostly different set, including tests that had been passing in Run 1 (`login page loads`, `register page loads`, several `collections.spec.ts` and `daily.spec.ts` tests).\n- Run 3 (same code, no changes): 18 failed again, yet another different subset (`sidebar has navigation links` failed here but hadn't in Run 2; `Search Page loads` failed here but hadn't in Run 1).\n- Running `e2e/app.spec.ts` alone, twice in a row, produced different results each time (3 failures once, 1 failure the next).\n\nThis is the same class of problem as `full-suite-only-flaky-tests-state-leak-across-test-files` (found earlier the same day on the *backend* suite) but on the frontend e2e suite instead. Suspected causes, not yet confirmed:\n\n1. **Auth-state ambiguity**: several failing tests assume an auth-enabled backend (`/login` should show a Login page with title matching `/Login/`) but `playwright.config.ts` never configures `PYRITE_CONFIG`/auth settings for the launched backend, so it runs with whatever `load_config()` resolves to (likely auth disabled by default) -- `/login` then redirects away, breaking any test that assumes it renders. This looks structural, not flaky, and would explain `auth.spec.ts` failures consistently -- but they don't fail consistently, which suggests something else varies run to run.\n2. **Shared KB/index state across the Playwright test run**: `entry-crud`, `qa`, `collections`, `timeline`, `search`, and `daily` specs all assert on the presence/absence of data (\"shows entry list or empty state\", \"shows issues list or clean state\", \"No timeline events found\"). If these tests run against a real KB directory that earlier tests in the same run mutate (create an entry, etc.), later assertions about \"empty state\" vs \"has entries\" become order-dependent -- classic shared-fixture flakiness.\n3. Possibly a race in backend startup timing under `webServer` (uvicorn + vite booting in parallel) causing some page loads to hit the backend mid-startup on a loaded machine.\n\n## Fix\n\n1. Bisect: run the suite serially (`--workers=1`, already effectively serial for single-worker local runs) several times back to back, diffing which specific tests fail each time, to separate \"genuinely flaky/order-dependent\" from \"deterministically broken given current fixture state.\"\n2. Decide the intended auth-state contract for e2e tests explicitly (a dedicated test config with auth enabled + a seeded user, or confirm auth-disabled is correct and fix/quarantine the auth.spec.ts tests that assume otherwise) -- mirrors the same \"what should this look like\" question the backend flaky-test ticket raises, just for the web layer.\n3. If shared KB/index state across specs is confirmed as a cause, give each e2e test file its own isolated KB fixture (or reset between files) rather than one shared backend instance for the whole suite run.\n\n## Related fixes (already shipped, this investigation)\n\n- Vite dev proxy was missing `/auth`, `/branding`, `/config` prefixes (only `/api` and `/health` were proxied to the backend) -- real product bug, any local-dev or e2e request to those paths 404'd against Vite itself. Fixed in vite.config.ts.\n- `e2e/app.spec.ts`'s \"loads and shows Pyrite branding\" test used a `name: /Pyrite/` locator that matched both the sidebar logo link and a later-added footer link to pyrite.wiki (strict-mode violation, not a real app bug) -- fixed to scope by `href=\"/\"`.\n\
  - Two backend tests (`test_collections_plugin.py`, `test_web_clipper.py`) walked `app.routes` directly, which broke against fastapi>=0.139's new `_IncludedRouter` internal representation. Fixed to use the stable `app.openapi()[\"paths\"]` public API instead (see ci-make-green-and-load-bearing item 4 commit).\n\n## Update 2026-09-16: the job is now NON-BLOCKING, and this ticket owns restoring it\n\n`continue-on-error: true` was added to the `e2e` job in `.github/workflows/ci.yml`.\n\nRationale: three other CI-config bugs were fixed the same day (below), which\nshould take `test` and `test-optional-deps` green -- but while `e2e` blocks on a\nsuite that fails differently every run, the overall CI run stays red regardless,\nand a permanently-red CI is the exact signal-destroying condition\n[[ci-make-green-and-load-bearing]] was written to end.\n\n**This ticket now owns flipping that back.** The `continue-on-error` line carries\na REVERT comment pointing here. Until it is removed, the frontend has NO enforced\ngate in CI -- which raises this ticket's stakes rather than lowering them: it is\nnow the only thing standing between the web UI and an untested merge path, on the\nsurface the shared-instance pilot peers actually use\n([[epic-shared-instance-readiness]] workstream 4).\n\n### Fresh evidence from CI runners (2026-09-16)\n\nThree fork-PR runs plus the dev baseline all failed `e2e`, confirming the\ndiagnosis above from clean runner environments rather than only local runs:\n\n- `locator('text=New Entry') resolved to 2 elements` (3 occurrences)\n- `locator('text=No entries found').or(locator('[href^=\"/entries/\"]').first()) resolved to 2 elements` (3 occurrences)\n- `expect(page).toHaveTitle(expected) failed`\n- multiple `expect(locator).toBeVisible() failed -- element(s) not found`\n\nThe strict-mode violations are the same class as the already-fixed `app.spec.ts`\nlogo/footer collision: locators matched against visible **text** rather than a\nstable role / `href` / test-id, so any later-added element carrying the same\nstring silently breaks a previously-passing test. That is a suite-wide\nlocator-strategy problem, not three isolated bugs -- a sweep for `text=`-based\nlocators belongs in the fix.\n\n### Related CI-config bugs fixed the same day (all separate from this ticket)\n\nThese were the *other* reasons CI was red; none are e2e's fault, and fixing them\nis what leaves this ticket as the remaining blocker:\n\n1. The `test` matrix installed `.[dev,postgres]`, but `dev` is test tooling only\n   (pytest/mypy/ruff) -- it pulls neither `typer`/`rich` (`cli`) nor\n   `bcrypt`/`fastapi` (`server`), and the core `dependencies` block doesn't\n   either. 70 test modules failed at COLLECTION with `ModuleNotFoundError` on all\n   three Python versions while pip still exited 0. Now `.[all,postgres]`.\n2. `-W error::DeprecationWarning` was unscoped, promoting third-party\n   deprecations (anyio's `BlockingPortal` alias) to hard errors -- any upstream\n   release could turn CI red with no pyrite change. Now scoped to `pyrite` and\n   `tests`.\n3. `tests/test_worktree_service.py` ran bare `git init`, which yields `master` on\n   GitHub runners while `GitService` hardcodes `main` -- six CI-only failures\n   (`pathspec 'main' did not match`). Now `git init --initial-branch=main`.\n\n## Acceptance criteria\n\n- `npm run test:e2e` run 3 times consecutively, same code, same machine: identical pass/fail set each time (currently: different every time).\n- The auth-state contract for e2e is explicit and documented (either in playwright.config.ts comments or a fixture setup file), not implicit in whatever `load_config()` happens to resolve to.\n- Zero e2e tests fail due to cross-spec shared state (verified by running each spec file in isolation vs. the full suite and confirming identical outcomes).\n- No spec identifies an element by bare visible text where a role, `href`, or `data-testid` would be stable (the strict-mode-violation class above).\n- **`continue-on-error: true` is removed from the `e2e` job in `ci.yml`** and a full CI run passes
  with e2e blocking again. This ticket is not done while that line survives.\n\n## Analysis 2026-09-18 (conductor): why the suite fails differently every run\n\nEvidence: eight consecutive failed `e2e` jobs on CI (2026-09-17/18), the ticket's\nown 2026-09-16 runner evidence, and the specs.\n\n**1. The suite has no test-data contract; it assumes a world.**\n`playwright.config.ts` starts `uvicorn pyrite.server.api:app` with no\n`PYRITE_*` environment and `reuseExistingServer: !CI`. Locally that is Mark's\nreal config (47 KBs, real daily notes, other sessions writing); on a CI runner\nit is an empty home: zero KBs, zero entries. Every spec then asserts on data:\nthe Dashboard heading and stat cards (the page renders its zero state with no\nKBs), \"shows edit button when daily note exists\", \"shows entry\", collections\nheadings. The failure signature confirms it: the same specs fail on every CI\nrun at 5.1–5.6 s, which is the default `expect` timeout — the page loaded, the\nelement never existed. Locally the failing set *shifts* because the world\nshifts (specs create daily notes in a real KB; the daily GET itself creates\ntoday's note — `web-daily-notes-view-side-effect`). \"Non-deterministic\" is the\nwrong name; the suite is deterministic on its input, and its input is\nundefined.\n\n**2. Locators keyed on visible text.** `text=New Entry`, `text=Daily Notes`,\n`locator('h1').first()` — every later-added element with the same words is a\nstrict-mode violation (the runner evidence: \"resolved to 2 elements\" ×6). The\nlogo/footer fix in `app.spec.ts` was one instance of a class.\n\n**3. Environment ambiguity.** Auth state is unspecified (specs for /login and\n/register assume auth pages exist); the backend `webServer` has a 15 s timeout\nthat a cold runner importing torch can exceed; nothing pins `PYRITE_AUTO_EMBED`.\n\nNone of the three is fixed by retries, which is why `retries: 2` only made the\njob three times slower.\n\n## Plan: foundation first, then mechanical fan-out\n\n**Package A — the deterministic world (one worker, Opus).**\n- `web/e2e/global-setup.ts`: create a temp `PYRITE_DATA_DIR`/`PYRITE_CONFIG_DIR`,\n  write a config with auth **disabled** explicitly, `PYRITE_AUTO_EMBED=0`,\n  seed one KB `e2e` with a fixed set of entries (people, events, notes, a\n  collection, a daily note for a fixed date) via `pyrite init` + `pyrite\n  create`; export the seed as constants in `web/e2e/fixtures.ts`.\n- `playwright.config.ts`: backend `webServer` gets that `env`;\n  `reuseExistingServer: false` always (a local run must never touch real KBs);\n  backend timeout 60 s; `retries: 0` (a flake must be visible, not absorbed).\n- Specs that write get unique titles (`uniqueTitle()` helper) or their own KB.\n- Fix or isolate the daily-GET side effect for the seeded world (it is also a\n  read-tier violation: `web-daily-notes-view-side-effect`).\n- Prove it: 5 consecutive green local runs, then 5 on CI by dispatch.\n- Record: this analysis into the ticket; ADR-0032 §3a \"Playwright on main\".\n\n**Packages B–G — one Sonnet worker per group, disjoint footprints, after A.**\nRewrite each spec against the seeded world: assertions on seeded data; roles,\n`href`s, or `data-testid` instead of text; add `data-testid` to the Svelte\ncomponent only where no role exists. Each package = spec file(s) + the\npage component(s) they touch, so no two packages share a file:\n  B: app.spec + settings.spec (layout, dashboard, settings pages)\n  C: auth.spec (login/register — decide: skip when auth disabled, or a second\n     project with auth enabled and a seeded user; A decides, B implements)\n  D: entry-crud.spec + entry-features.spec (entries pages)\n  E: collections.spec + daily.spec\n  F: graph.spec + timeline.spec\n  G: qa.spec + search.spec\nAcceptance per package: its specs pass 5× in a row against A's world; zero\n`text=` locators; no `.first()` to dodge a strict-mode violation.\n\n**Package H — wire it in (Sonnet, after B–G).** `e2e` job runs on pushes to\n`main` (the value chain's depth layer) with `retries: 0`; the report artifact\nstays;
  the `continue-on-error` line goes; `tests/test_dev_process_config.py`\npinned. On `dev` pushes only after ten consecutive greens on `main`.\n\nSequencing: A alone (it changes the config every package depends on); B–G in\nparallel from the merged A; H last. Three conductor ticks."
file_path: /Users/markr/pyrite-wt/feature-playwright-foundation/kb/backlog/playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap.md
id: playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap
title: 'Playwright e2e suite: non-deterministic failures, likely shared state + auth-config gap'
type: backlog_item
tags:
- bug
- ci
- testing
- e2e
importance: 5
status: in_progress
priority: high
assignee: agent:conductor
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

## Package A result (2026-09-18): the world is defined; three causes found, one was ours

Delivered: `web/e2e/global-setup.ts` (the seed), `web/e2e/fixtures.ts` (the
contract), `web/e2e/seed.spec.ts` (the foundation's own tests), and the
`web/playwright.config.ts` changes. Branch `feature/playwright-foundation`,
PR #38.

### The world

A private `web/.e2e-data` per run — wiped and rebuilt every invocation, so no
run inherits another's writes. `PYRITE_DATA_DIR`/`PYRITE_CONFIG_DIR` point the
backend at it and nothing else; auth is disabled explicitly
(`PYRITE_AUTH_ENABLED=false`, asserted by a test rather than inferred);
`PYRITE_AUTO_EMBED=0` + `HF_HUB_OFFLINE=1` keep torch and the Hugging Face hub
off the write path. One KB `e2e` from the `research` template holding 3 person,
3 dated event, 2 note, 1 organization, 1 query collection, and 7 daily notes.
`reuseExistingServer: false` on both servers (a local run must never reach a
real KB), backend timeout 60 s, `retries: 0`.

`fixtures.ts` exports every one of those as a constant, plus `uniqueTitle()`
for specs that write and `idForTitle()` mirroring `generate_entry_id`.

### The daily-GET side effect

`get_or_create_daily_note` is already fixed for the read tier
(`web-daily-notes-view-side-effect`): a caller below write tier gets 404
instead of a created note. But with auth disabled `verify_api_key` resolves
every caller to `admin`, so in THIS configuration the GET does create — by
design, not a bug, and no code change was warranted. The seed instead
pre-creates every date the specs can navigate to (today ±3, plus a fixed
2020-03-04), which makes each of those GETs a read. `seed.spec.ts` asserts it:
it snapshots `/api/daily/dates`, GETs yesterday/today/tomorrow, and asserts the
date list is unchanged.

### Two bugs found in Package A's own remit, fixed here

1. **The seed ran once per worker, not once per run.** `playwright.config.ts`
   is evaluated in the main runner process AND again in every worker process,
   so five workers plus the parent wiped and rebuilt the data directory
   concurrently: 118 of 119 tests errored at 0 ms inside `pyrite create`.
   Guarded by a marker in `process.env`, which workers inherit because they are
   forked with `{...process.env}` (`runner/processHost.js`).

   Related and load-bearing: the seed runs at config-module scope rather than
   through Playwright's `globalSetup` hook, because `webServer` starts in a
   plugin setup task and plugin setup tasks run BEFORE globalSetup tasks
   (`runner/tasks.js: createGlobalSetupTasks`). The backend reads its config
   once at import, so a globalSetup reseed happens after the server has already
   read an empty directory. Observed: 6 of 9 seed tests failing until the call
   moved.

2. **The read rate limiter made the failing set move.** Five workers share one
   client IP and exhaust `rate_limit_read: 100/minute` partway through a run;
   whichever page loses renders "API Error 429" instead of its content. Across
   the first five-run batch, `graph.spec.ts:34` failed in exactly the three runs
   whose logs contain a 429 and passed in the two that do not. Fixed with
   `RATELIMIT_ENABLED=false` (slowapi's own switch, read from the environment)
   for the test backend only. Measured on the seeded backend, 150 sequential
   reads of `/api/kbs`: limiter on → 100×200 + 50×429; limiter off → 150×200.
   `seed.spec.ts` asserts the limiter is off.

### Two product bugs found, NOT fixed here (ADR-0033)

Both are real user-facing bugs in the web app, both outside Package A, and both
are what remains of the moving failure set:

- **#49 — the root layout overwrites every page title with the brand name.**
  `+layout.svelte` assigns `document.title = brandStore.name` in an `$effect`,
  clobbering every route's `<svelte:head><title>`. Probed all ten top-level
  routes: every one returns `"Pyrite"`. Users get the same tab title everywhere.
  It is also a race — whether the page title or the branding effect lands last
  depends on when `/config/branding` returns — which is why `search.spec:4` and
  `settings.spec:4` fail the `toHaveTitle` in 5 of 5 runs while `qa.spec:4` and
  `daily.spec:4`, the same assertion, fail in 4 of 5.
- **#45 — the entries page flashes "No entries found" before the KB store
  resolves.** The list `$effect` is a no-op while `kbStore.activeKB` is null, so
  `entryStore.loading` is still false and `EntryList` renders its empty state
  before any request has been made. Against a KB with 17 entries,
  `app.spec:58` failed in 2 of 5 runs and `entry-crud:36`/`entry-crud:4` in 1 of
  5 — the latter because the empty state's own "New Entry" action button becomes
  a second `New Entry` link and turns the assertion into a strict-mode
  violation.

### Evidence

Five consecutive `npm run test:e2e`, same code, same machine, after the fixes:

| run | failed | skipped | passed | wall |
|---|---|---|---|---|
| 1 | 14 | 19 | 87 | 25.4s |
| 2 | 14 | 19 | 87 | 26.3s |
| 3 | 12 | 19 | 89 | 24.8s |
| 4 | 13 | 19 | 88 | 25.0s |
| 5 | 13 | 19 | 88 | 40.7s |

Eleven specs fail in all five runs — the stable core, which is what packages
B–G are for (`text=` locators, data assumptions, auth pages under
auth-disabled):

```
app.spec.ts:14         Dashboard > shows dashboard heading
app.spec.ts:19         Dashboard > displays stat cards
auth.spec.ts:4         Login Page > login page loads
auth.spec.ts:69        Register Page > register page loads
collections.spec.ts:4  Collections Page > loads and shows collections heading
entry-crud.spec.ts:13  Entries Page > has type filter dropdown with "All types" default
entry-crud.spec.ts:20  Entries Page > has sort controls
entry-crud.spec.ts:45  New Entry Page > new entry button navigates to creation form
entry-crud.spec.ts:74  New Entry Page > breadcrumbs show entries link and new entry label
search.spec.ts:4       Search Page > loads and shows search heading
settings.spec.ts:4     Settings Page > loads and shows settings heading
```

Four vary, and every one of them is accounted for by #49 or #45 above:
`qa.spec:4` (4/5, #49), `daily.spec:4` (4/5, #49), `app.spec:58` (2/5, #45),
`app.spec:77` (1/5, #45 — the empty state's own "New Entry" action button
becomes a second `New Entry` link and turns the assertion into a strict-mode
violation). Nothing else moved, and no run contained a real 429.

Honest caveat on the "identical set" criterion: it is NOT yet met, and cannot
be met from inside Package A. The four movers are the two product bugs, which
are races by construction; the set becomes identical when #49 and #45 are
fixed, not when the harness improves. A second ten-run sample (two batches of
five) gave the same eleven-test stable core and the same two causes; one run in
that sample stalled to 1.3 m with nine `page.goto` timeouts because a sibling
worker's pytest suite was running concurrently (load average 5-6). That is
machine contention, not the suite — `seed.spec.ts` passed all ten of its
assertions in all fifteen runs across all three batches, including the stalled
one.

No run touched the real config directory. Before and after the batch:

```
2026-08-28T06:07:54 637804544 /Users/markr/.pyrite/index.db
2026-08-20T16:37:11        27 /Users/markr/.pyrite/config.yaml
```

Identical mtime and size on both, which is what `reuseExistingServer: false`
plus `PYRITE_DATA_DIR` buys: a local run can no longer reach a real KB.

`seed.spec.ts` — the ten assertions on the world itself — passed in all five
runs, and in all fifteen runs across the three batches taken during this work.

### Left for the packages that follow

- B–G still own the spec rewrites, and they should now assert on
  `fixtures.ts` constants instead of "list or empty state" disjunctions. The 19
  `test.skip`-on-missing-data skips in `entry-crud`/`entry-features`/`graph`
  should become real assertions against seeded entries.
- C's question is answered: auth is disabled, so `/login` and `/register` are
  not the app's operating mode. `AUTH_ENABLED` in `fixtures.ts` is the constant
  to branch on; either skip those specs or give them a second project with auth
  enabled and a seeded user.
- The suite cannot be green while #49 and #45 are open — they are product bugs,
  not test bugs, and packages B/D/G will hit them head-on.
- H still owns `ci.yml` and the `continue-on-error` line.
