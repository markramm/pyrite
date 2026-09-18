---
id: playwright-package-a-1-per-worktree-ports-and-data-dir-118
title: 'Playwright package A.1: per-worktree ports and data dir (#118)'
type: backlog_item
tags:
- testing
- playwright
- e2e
- milestone-0.24.2
kind: bug
status: done
priority: high
assignee: agent:pyrite-worker
effort: S
---

## Theme: Playwright package A.1 — per-worktree ports and data dir (#118)

Closes #118. Milestone 0.24.2. `heavy: yes` (Playwright verification runs). Model: sonnet.

### Why

`web/playwright.config.ts` hardcodes the backend to 8088 and Vite to 5173 with `reuseExistingServer: false`. Two worktrees running `playwright test` at once collide: Vite silently falls back to 5174+ while the health check and `baseURL` stay on 5173, so a run talks to a *sibling worktree's* backend and world, and the uvicorn on 8088 drops mid-run under load. Packages C/D/E ran three at once on 2026-09-18 and their evidence was contaminated; Playwright has been serialized to one worktree at a time since. This package removes the reason.

### Acceptance

1. Ports and the data dir are derived per worktree: `PLAYWRIGHT_E2E_PORT` (backend) and `PLAYWRIGHT_E2E_VITE_PORT` when set, else a stable hash of the worktree path mapped into a high range (e.g. 20000–29999, backend and Vite distinct); `web/.e2e-data` becomes `web/.e2e-data-<port>` or equivalent so two worktrees never share a world. `scripts/new-worktree.sh` exports/records the chosen ports (a `.pyrite/e2e-ports` file or the config's env) so a human running the suite by hand gets the same ones.
2. A preflight in `global-setup.ts` fails fast — a clear error naming the port and the owning process (`lsof -i :<port>`) — when the target port is already bound by a process outside this worktree. Vite's silent fallback is defeated: `strictPort: true` on the Vite webServer command (or the config's equivalent) so a taken port is an error, never a different port.
3. The `baseURL`, both `webServer.url` health checks, and any `/api` proxy target read the same derived ports; nothing in `web/e2e/*.spec.ts` needs to change.
4. Evidence: two worktrees (this one and a throwaway second `scripts/new-worktree.sh` from `origin/dev` with this branch cherry-picked) run `npm run test:e2e` **concurrently**; each passes `seed.spec.ts` against its own world, `lsof` shows two distinct port pairs, and neither run's log contains `trying another one`, `already used`, `ECONNREFUSED` or `was not able to start`. Then five sequential runs in this worktree: the same failing set every time (the known eleven from package A, minus whatever B–E fixed), and `~/.pyrite/index.db` mtime unchanged.
5. The config comment about never reusing a server on 8088 stays true in spirit (never reuse a server this worktree did not start). CHANGELOG line. The Playwright ticket's "Package A.1" section appended with the port scheme and the evidence.

### Touches

Existing: `web/playwright.config.ts`, `web/e2e/global-setup.ts`, `web/e2e/fixtures.ts` (only if the data-dir constant lives there), `scripts/new-worktree.sh`, `.gitignore` (the new data-dir pattern), `CHANGELOG.md`, `kb/backlog/playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap.md`.
New: none expected.
Out of scope: rewriting any spec file (F/G), `ci.yml` (H), the server's own port handling.

## Result (2026-09-18): ports and data dirs are per-worktree; two worktrees run concurrently

Delivered: `web/e2e/ports.ts` (the pure port-derivation module, with its own
vitest unit tests — `web/e2e/ports.test.ts`), `web/e2e/print-ports.ts` (a CLI
wrapper for `scripts/new-worktree.sh` and a human's shell), plus edits to
`web/e2e/global-setup.ts`, `web/e2e/auth-setup.ts`, `web/playwright.config.ts`,
`web/vite.config.ts`, `scripts/new-worktree.sh`, `.gitignore`, `CHANGELOG.md`.
Branch `feature/playwright-a1-ports`.

### The scheme

Four ports (base backend, base Vite, auth backend, auth Vite) derive from a
SHA-256 hash of the worktree's own filesystem path, each in its own disjoint
1/4 band of 20000–29999 so the four cannot collide with each other by
construction. `PLAYWRIGHT_E2E_PORT` / `PLAYWRIGHT_E2E_VITE_PORT` override the
base pair. Both data directories are suffixed with the derived backend port
(`web/.e2e-data-<port>`, `web/.e2e-auth-data-<port>`) so two worktrees never
share, or race to wipe, one directory. `web/vite.config.ts` gained
`strictPort: true` (it had none before; only the auth world's
`vite.e2e-auth.config.ts` did) and a `PLAYWRIGHT_E2E_PORT`-driven proxy
target, so the same derived port reaches both the uvicorn command and the
dev server proxying to it — plain `npm run dev` is unaffected, defaulting to
8088 as before. `global-setup.ts` and `auth-setup.ts` each gained a
`preflightPort()` check (`lsof -i :<port>`) that fails fast, naming the port
and the owning process, before either world starts building.

One gap found and closed while implementing: five spec files
(`app.spec.ts`, `entry-crud.spec.ts`, `entry-features.spec.ts`,
`graph.spec.ts`, `seed.spec.ts`) independently hardcoded a direct-to-backend
API base URL of their own (bypassing Vite's proxy for API-only assertions).
The acceptance criteria's "nothing in `web/e2e/*.spec.ts` needs to change"
was a promise about the port *mechanism*, not license to leave five files
pointed at a literal `8088` the config no longer starts anything on — so
each was changed to import the new `E2E_BACKEND_URL` constant from
`global-setup.ts` instead. This is a one-line-per-file substitution, not a
rewrite; F/G's out-of-scope spec rewrites are untouched.

A second gap: Playwright's default `testMatch` also matches `*.test.ts`, so
without an explicit `testMatch: /.*\.spec\.ts/` on the config, Playwright
tried to run `ports.test.ts` (a vitest unit test) as its own spec and
crashed loading vitest's `expect` into a Playwright worker process. Scoped
to `*.spec.ts`, which every real spec in the suite already used.

### Evidence

**Concurrent, two worktrees.** `feature-playwright-a1-ports` (base) and a
throwaway `feature-playwright-a1-ports-throwaway` (from `origin/dev`, this
branch's commit cherry-picked) ran `npm run test:e2e` at the same time.
Derived ports were fully distinct: base (21764, 24384, 25926, 29231),
throwaway (20152, 24536, 26077, 27864). An `lsof` snapshot taken mid-run
shows all eight simultaneously LISTENing, each with ESTABLISHED connections
from its own worktree's Chromium and Node processes only — zero overlap.
Both runs passed all 10/10 `seed.spec.ts` assertions against their own
separate seeded worlds. Base: 128 passed, 0 failed. Throwaway: 126 passed, 2
failed (`qa.spec.ts:4`, `search.spec.ts:4` — both issue #49, the pre-existing
page-title race, not a port issue). Grepping both full run logs for `trying
another one`, `already used`, `ECONNREFUSED`, `was not able to start`:
zero matches in either.

**Five sequential runs, this worktree**, machine otherwise idle (an initial
batch of five ran concurrently with a sibling worktree's `pytest` and
macOS Spotlight reindexing — load average 13–24 — and is not used as
evidence; a clean batch was taken after):

| run | failed | skipped | passed |
|---|---|---|---|
| 6 | 2 | 4 | 126 |
| 7 | 2 | 4 | 126 |
| 8 | 2 | 4 | 126 |
| 9 | 3 | 4 | 125 |
| 10 | 2 | 4 | 126 |

Four of five runs failed exactly `qa.spec.ts:4` and `search.spec.ts:4` (both
#49). Run 9 additionally failed `app.spec.ts:26`, taken during residual
Spotlight-indexing load; not reproduced in runs 6/7/8/10 under the same
code. This matches the parent ticket's own documented caveat that the
"identical set" criterion cannot be fully met until #49/#45 are fixed — that
remains true here; A.1 changes only the ports, not those two races.

`~/.pyrite/index.db` (size 637804544) and `~/.pyrite/config.yaml` (size 27)
were checked by `stat` before the first run of this work and after the last
(concurrent run plus fifteen sequential runs across both batches): identical
mtime and size throughout. No run touched the real config.

### Left for later packages

- H still owns `ci.yml`.
- #49 and #45 remain open product bugs; not this package's remit.
- `web/e2e/print-ports.ts` is a convenience for a human's shell and
  `scripts/new-worktree.sh`; nothing in the test run itself reads
  `.pyrite/e2e-ports` — the config derives the same values independently at
  test time, so the file cannot drift out of sync with what a run actually
  uses.
