---
id: playwright-package-h-the-e2e-job-blocks-on-main
title: 'Playwright package H: the e2e job runs on main, blocking, retries 0'
type: backlog_item
tags:
- testing
- e2e
- ci
- playwright
importance: 5
kind: task
status: proposed
priority: high
effort: S
rank: 0
---

Package H of [[playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap]]; closes that ticket, which the roadmap's 0.24.2 "every interface has an end-to-end test in CI — Web" line names.

## Acceptance (verbatim)

Package H: "`e2e` job runs on pushes to `main` (the value chain's depth layer) with `retries: 0`; the report artifact stays; the `continue-on-error` line goes; `tests/test_dev_process_config.py` pinned. On `dev` pushes only after ten consecutive greens on `main`."

The ticket's own: "**`continue-on-error: true` is removed from the `e2e` job in `ci.yml`** and a full CI run passes with e2e blocking again. This ticket is not done while that line survives." — and — "`npm run test:e2e` run 3 times consecutively, same code, same machine: identical pass/fail set each time."

## Groom 2026-09-18 (serial)

**Regimes:** a pull request (the job must not run); a push to `dev` (must not run); a push to `main` (runs, blocking); `workflow_dispatch` on any branch (runs — it is the only way to get evidence before the merge); a docs/KB-only push to `main` (the `changes` classifier — say whether e2e runs; a release fast-forward is never docs-only, so "skip" is acceptable if stated); **a cold runner** — every CI run is the first run after the servers start, which is exactly #153's failing condition, so H is not evidence-complete until #153 is fixed or shown not to reproduce on a runner.

**Touches** — existing: `.github/workflows/ci.yml` (the `e2e` job ~:276 — `if:` becomes push-to-`main` or `workflow_dispatch`; `continue-on-error` ~:301 and its REVERT comment block go; the job declares `permissions:` per the pin that landed in 28fc380), `tests/test_dev_process_config.py`, the Playwright ticket (status → done, moved to `backlog/done/`). `web/playwright.config.ts` is already `retries: 0` — not touched. New: none.

**Sequence:** last of the Playwright line — after package F (#160), package G and #153 have merged; after #163 and the suite-lock item (all edit `ci.yml` and/or `tests/test_dev_process_config.py`).

**Model:** sonnet. **heavy:** no for the diff; the evidence is 3 consecutive local full-suite runs (heavy, one slot each) **plus** 3 green `workflow_dispatch` runs of the `e2e` job on the branch. **Cold read:** yes — it changes a gate, and a wrong `if:` runs e2e on every PR or on nothing, invisibly. **Size:** S, ~60 lines.

**Couplings:** `e2e` must not enter `gate`'s `needs`, and `scripts/release.py`'s CI wait must not wait on it — it runs on `main`, i.e. after the release fast-forward; it is the depth layer, not a release gate. Evidence gap: "passes on `main`" cannot be shown from a branch; the conductor watches the first real `main` run at the 0.24.2 release.

**Decision flagged for the maintainer:** `main` moves only at releases, so "ten consecutive greens on `main`" is ten releases unless `workflow_dispatch` runs against `main` count. Not this theme's to settle; the `dev` trigger stays off either way.

**Out of scope:** the `dev` trigger; spec rewrites; package A's world; #162.
