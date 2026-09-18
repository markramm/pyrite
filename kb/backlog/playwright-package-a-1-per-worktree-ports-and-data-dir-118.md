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
status: in_progress
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
