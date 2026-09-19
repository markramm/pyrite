---
id: playwright-package-g-qa-and-search-specs-against-the-seeded-world
title: 'Playwright package G: qa and search specs against the seeded world'
type: backlog_item
tags:
- testing
- e2e
- web
- playwright
importance: 5
kind: task
status: proposed
priority: high
effort: S
rank: 0
---

Package G of [[playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap]] — the last spec rewrite before package H makes the `e2e` job blocking. Same shape as packages D, E and F.

## Acceptance (the ticket's B–G block, verbatim)

"Rewrite each spec against the seeded world: assertions on seeded data; roles, `href`s, or `data-testid` instead of text; add `data-testid` to the Svelte component only where no role exists." — "Acceptance per package: its specs pass 5× in a row against A's world; zero `text=` locators; no `.first()` to dodge a strict-mode violation."

Plus, from #9's criterion 2: `search.spec.ts` asserts that a query for a seeded entry renders that entry's title as a result link (the rendered list, not only the "N results" header).

## Groom 2026-09-18 (serial)

**Regimes:** a search with zero results against the seeded world (the empty state, asserted by role/testid, not `text=No results found`); a query matching more than one seeded entry (no `.first()` — assert on the seeded id's `href`); the QA page's loading state (assert it *ends*, never assert on `Loading QA data...`); QA against a world with zero issues and — only if the seed has one — with an issue; the first navigation after server start (#153's class: if a spec fails in ~170 ms on run 1 and passes warm, report it against #153, do not add a retry).

**Touches** — existing: `web/e2e/qa.spec.ts` (56 lines; `text=QA Dashboard`, `text=Loading QA data...`, `text=Total Entries`, `text=No issues found.` — 6 `text=`), `web/e2e/search.spec.ts` (92 lines; `text=No results found`, `a[href^="/entries/"].first()` — 3 `text=`); only where no role exists: `web/src/routes/qa/+page.svelte`, `web/src/routes/search/+page.svelte` (a `data-testid`, nothing else). New: none.

**Sequence:** after #49 (page titles) merges — both specs open with a `toHaveTitle` that fails 5/5 (search) and 4/5 (qa) today because of #49; with #49 fixed they are kept as real assertions, not skipped. After #160 (package F) merges, for the shared ticket file only. Before package H. Before any #9 fix (both touch `web/src/routes/search/+page.svelte`).

**Model:** sonnet. **heavy: yes** — 5 consecutive runs of the two spec files plus one full-suite run as the closing evidence; each takes the machine's one slot (`scripts/e2e.sh` once it exists; otherwise nothing else running). **Cold read:** no. **Size:** S, ~150 changed lines, 2–4 files.

**Out of scope:** root-causing #9 — do not touch `web/src/lib/stores/search.svelte.ts`; package A's files (`global-setup.ts`, `fixtures.ts`, `playwright.config.ts`) — a missing seed is reported, not added; the `e2e` CI job (H); #162's links.
