# Theme: Playwright package B — app.spec + settings.spec against the seeded world

Dispatched by the conductor, tick 2 of 2026-09-18. This file is your authority:
re-read it if you lose context.

**Worktree:** `/Users/markr/pyrite-wt/feature-playwright-package-b`
**Branch:** `feature/playwright-package-b`
**Draft PR (the claim):** opened by the conductor; do not open another, and do
not flip it to ready — the conductor reviews and does that.

## Ticket

`kb/backlog/playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap.md`,
section **"Plan: foundation first, then mechanical fan-out"**, Package B.
Package A merged as PR #38 and is on `dev`: the deterministic world
(`web/e2e/global-setup.ts`, `web/e2e/fixtures.ts`, `web/playwright.config.ts`)
already exists. Read `web/e2e/fixtures.ts` first — it is the contract between
the seed and the specs, and it documents the auth decision Package A made
(auth is explicitly DISABLED; every caller resolves to admin).

## Scope: exactly two spec files

- `web/e2e/app.spec.ts` (Dashboard, Sidebar Navigation, Entries/Search/Timeline/
  Daily/Graph/Settings page-load describes)
- `web/e2e/settings.spec.ts`

Rewrite both against the seeded world.

## Acceptance criteria (from the ticket, verbatim where it is verbatim)

1. Both specs assert on **seeded data** from `web/e2e/fixtures.ts` — not on
   "either a list or an empty state". The world is defined now; an assertion
   that passes either way tests nothing. Example: the Entries page must show
   the seeded people/events/notes by their known titles or ids, not "entries
   or 'No entries found'".
2. **Zero `text=` locators** in these two files. Use `getByRole`, `href`, or a
   `data-testid`. Add a `data-testid` to the Svelte component only where no
   role or href is stable — and when you do, that component file becomes part
   of this package's footprint, so note it in your report.
3. **No `.first()` used to dodge a strict-mode violation.** If a locator matches
   two elements, scope it (by container, role name, or href) so it matches one.
   `.first()` is allowed only where matching the first of a genuinely repeated
   list is the intent, and then say so in a comment.
4. Its specs pass **5× in a row** against A's world:
   `cd web && for i in 1 2 3 4 5; do npx playwright test e2e/app.spec.ts e2e/settings.spec.ts || break; done`
   Paste the five results in your report. Identical pass set each time.
5. `cd web && npm run build && npm run test:unit` still passes.
6. If a spec fails because the **app** is wrong (a real product bug, not a bad
   locator), do NOT paper over it with a weakened assertion. Fix it if it is a
   one-line fix inside your footprint; otherwise leave the assertion correct,
   mark the test `test.fixme` with a comment naming the bug, and report it so
   the conductor files an issue.

## Files

**Existing, to be rewritten:** `web/e2e/app.spec.ts`, `web/e2e/settings.spec.ts`
**Existing, patched minimally if and only if criterion 2 requires it:** the
Svelte components those two specs drive (`web/src/routes/+page.svelte`,
`web/src/routes/settings/**`, `web/src/lib/components/**` — only the ones you
actually need a `data-testid` on).
**Read-only, do not edit:** `web/e2e/fixtures.ts`, `web/e2e/global-setup.ts`,
`web/playwright.config.ts`, `web/e2e/seed.spec.ts` — Package A owns them. If
you believe one of them is wrong, report it; do not change it.

## Out of scope (hard boundaries — other packages own these)

- Every other spec under `web/e2e/`: `auth.spec.ts` (C), `entry-crud.spec.ts`
  and `entry-features.spec.ts` (D), `collections.spec.ts` and `daily.spec.ts`
  (E), `graph.spec.ts` and `timeline.spec.ts` (F), `qa.spec.ts` and
  `search.spec.ts` (G). Do not touch them even to fix an obvious bug —
  packages C–G are dispatched in parallel with you and will conflict.
  app.spec.ts's page-load describes for those pages stay in app.spec.ts;
  they are "the page loads", not the page's behaviour.
- `.github/workflows/ci.yml` — Package H owns it. The `continue-on-error` line
  on the `e2e` job stays.
- Any Python code, `pyrite/`, `tests/`.

## Model / process

Load the `pyrite-dev` skill and follow it. Use this worktree's `.venv`.
Commit at whatever pace the work needs; push the branch. **Do not open a PR**
(one exists) and do not flip it to ready. When the theme is complete, reply
with the pyrite-dev report format, including the 5× run output and any
product bug found under criterion 6.
