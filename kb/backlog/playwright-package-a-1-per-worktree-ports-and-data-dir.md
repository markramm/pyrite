---
id: playwright-package-a-1-per-worktree-ports-and-data-dir
title: 'Playwright package A.1: per-worktree ports and data dir'
type: backlog_item
tags:
- process
importance: 5
status: proposed
priority: medium
rank: 0
---

Fixes #118. `web/playwright.config.ts` hardcodes the e2e backend to 8088 and Vite to 5173 with `reuseExistingServer: false`, so two worktrees running `playwright test` concurrently talk to each other: Vite silently falls back to 5174+ while the health check and `use.baseURL` still point at 5173 (a sibling worktree's backend answers), and the uvicorn on 8088 drops mid-run under load 22-33.

## Acceptance criteria

- Ports and the `web/.e2e-data` directory name are derived per worktree -- from the worktree path, or from `PLAYWRIGHT_E2E_PORT` exported by `scripts/new-worktree.sh`.
- The run fails fast with a clear message when a target port is already bound, instead of silently binding another port and testing against a stranger.
- `use.baseURL` and `webServer.url` cannot disagree with the port actually bound.
- Two worktrees can run `playwright test` concurrently without data bleed. Demonstrate it.

## Scope

Allowed to touch package A's four files -- that boundary was set for packages B-G and does not bind this item.

## Why it goes first

Packages F, G and H must not be dispatched until this lands: until then Playwright runs are one-at-a-time, not two. The "machine-heavy" cap from retro 2 named the symptom; the shared fixed ports were the fault the file footprint could not see -- two themes can be footprint-disjoint in git and still collide on a port, which is a footprint dimension the dispatch rules do not currently model.

Also note for review of #82 (package C) and #83 (package D): their five-run evidence may be contaminated by a sibling's world. Re-run their suites with no other Playwright process alive (`lsof -i :8088 -i :5173` empty first) and treat any log line containing `trying another one`, `already used`, `ECONNREFUSED` or `was not able to start` as an invalid run, not a failure.
