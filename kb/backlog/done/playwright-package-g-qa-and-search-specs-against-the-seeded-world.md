---
id: playwright-package-g-qa-and-search-specs-against-the-seeded-world
title: 'Playwright package G: qa and search specs against the seeded world'
type: backlog_item
tags:
- testing
- e2e
- web
- playwright
- quality
importance: 5
kind: task
status: done
priority: high
effort: S
rank: 0
assignee: agent:pyrite-worker
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

## Groom 2026-09-19 (architect — dispatchable; supersedes the 09-18 sequence)

This re-groom exists because two things changed since 09-18: package F merged
(#160) and set the conventions this package copies, and the spike on #9
(`## Spike 2026-09-19` on the issue) made **this package's first assertion the
condition for closing #9**. The 09-18 sequence said "after #49 merges"; #49 is
still open and package F did not wait for it — F's rewritten
`timeline.spec.ts` and `graph.spec.ts` carry **no `toHaveTitle` at all**. G
follows F: drop the two `toHaveTitle` assertions rather than skip them, with a
comment naming #49, and the sequence blocker is gone. **G is dispatchable now.**

### Acceptance

1. **The #9 criterion, first.** `search.spec.ts` types a seeded query into the
   search input, and asserts that the seeded entry's title renders **as a
   result link** — `a[href="/entries/e2e-note-alpha"]` (the id comes from
   `web/e2e/fixtures.ts`; the page builds the href with
   `encodeURIComponent(result.id)`, and the seeded ids are already
   URL-safe) containing the text `E2E Note Alpha` — and that the skeleton is
   gone (`.animate-pulse` at count 0 in the results area) at the moment that
   link is visible. Not the "N results" header alone: the header and the
   skeleton are mutually exclusive guards
   (`web/src/routes/search/+page.svelte:257` and `:360`), so an assertion on
   the header cannot distinguish a rendered list from a stuck one. **The
   worker's report must quote this test by file and line** — the conductor
   closes #9 citing it, per the spike's recommendation 2.
2. Both specs assert on the seeded world from `fixtures.ts` (`SEEDED_NOTES`,
   `SEEDED_PEOPLE`, `SEEDED_ENTRIES`, `E2E_KB`) — never on "results or an
   empty state". Every `.or(...)` and every `if (count > 0) { … }` in today's
   two files is removed: a page stuck on a skeleton satisfies neither branch
   of the `.or()` and takes the `if`'s false path, so both forms pass while
   the product is broken. That is the whole point of the package.
3. Zero `text=` locators (today: 3 in `search.spec.ts`, 6 in `qa.spec.ts`).
   No `.first()` used to dodge a strict-mode violation. `data-testid` added to
   a page **only where no role, label or `href` identifies the element**, and
   each one named in the report.
4. Both spec files pass **5× in a row** against A's world, using this
   worktree's derived ports (`node web/e2e/print-ports.ts <repo-root>`), plus
   one full-suite run as the closing evidence. A run whose log contains
   `trying another one`, `already used`, `ECONNREFUSED` or
   `was not able to start` is an invalid run, not a failure.
5. A real product bug found by a now-real assertion is filed as a GitHub issue
   and marked `test.fixme` naming that issue — never papered over, never
   softened back into a conditional.
6. Package A's files are not edited; a missing seed is reported, not added.

### What the code actually offers (so the spec names real selectors)

Read on `dev` @130f433 — these are the handles, and where a `data-testid` is
warranted:

- **Search page has no heading.** `Topbar` renders a breadcrumb, not an `h1`
  (`web/src/lib/components/layout/Topbar.svelte` has no `h1`/`role`), which is
  why today's spec reaches for `header nav >> text=Search`. There is no role to
  switch to: this is a legitimate `data-testid` (on the Topbar's title/
  breadcrumb element, or on the search page's own container) — or drop the
  "shows the heading" test, since the input and the result assertions already
  prove the route rendered. Worker's call; say which in the report.
- **Search input**: `input[placeholder="Search entries..."]` —
  `getByPlaceholder('Search entries...')` is a real accessible locator, keep it.
- **Mode buttons** (`keyword` / `semantic` / `hybrid`): plain `<button>` with
  text, so `getByRole('button', { name: 'keyword' })` works. Today's spec
  asserts the active state with `toHaveClass(/bg-gold/)`; the real class is
  `bg-gold-500/20 text-gold-400 border border-gold-500/50`. Asserting on a
  Tailwind class is styling-coupled and will break on a restyle — prefer
  asserting the **behaviour**: after clicking `semantic`, a seeded query still
  returns the seeded entry's link. If an active-state assertion is kept, it
  needs `aria-pressed` on the button (an accessibility improvement, and the
  one behaviour-adjacent page edit this package may make) rather than a class
  regex.
- **Result count**: a bare `<span>` under
  `{#if !searchStore.loading && searchStore.query.trim() && searchStore.results.length > 0}`
  (`+page.svelte:257`). No role. Either `data-testid="search-result-count"` or
  assert only on the links — the links are the stronger assertion.
- **Result links**: `<a href="/entries/{encodeURIComponent(result.id)}">` with
  the title in a `<span class="font-medium">` (`:384`–`:393`). Assert
  `page.locator('a[href="/entries/<seeded-id>"]')` +
  `toContainText(<seeded title>)`, exactly as F's `timeline.spec.ts` does.
- **Search empty state**: a `<div>` with `No results found` at `:369`. No role
  and no testid — `data-testid="search-empty-state"` is warranted here; assert
  on it for the zero-result regime, not on the words.
- **Search skeleton**: `SkeletonLoader variant="search"` at `:360`, whose
  markup is `div.animate-pulse` (`web/src/lib/components/common/SkeletonLoader.svelte:49`).
  `.animate-pulse` is usable as-is for a `toHaveCount(0)`; a
  `data-testid="search-skeleton"` on the results container's skeleton branch is
  cleaner and makes the #9 assertion read plainly. Either is acceptable.
- **Both KB `<select>`s are unlabeled** (search `:214`, qa `:82`) — no
  `<label>`, no `aria-label`, so `getByLabel` cannot reach them and
  `filter({ hasText: 'All KBs' })` is the text-coupled workaround in use today.
  Adding `aria-label="Filter by knowledge base"` / `"Filter by severity"` is an
  accessibility fix, in scope, and preferable to a testid. Same for the search
  page's type filter (`:224`) and the QA severity filter (`:90`).
- **QA page**: `Topbar title="QA Dashboard"` (again no heading role);
  `LoadingState message="Loading QA data..."` at `:100` (a `div.animate-spin`,
  no role — assert the loading state **ends** by waiting for a stat card, never
  assert on the message); stat cards are plain `<div>`s with a label `<div>`
  and a value `<div>` (`:107`–`:125`) — `data-testid="qa-stat-total-entries"`
  and `"qa-stat-total-issues"` (or a single testid on the grid plus
  `getByText` on the value) are warranted, there is no role; the issues section
  has a real `<h2>Issues (N)</h2>` at `:180` —
  `getByRole('heading', { name: /^Issues \(\d+\)$/ })` works today; the clean
  state is a `<div>No issues found.</div>` at `:183` needing a testid; each
  issue row is a `<tr>` inside a `<table>` — `getByRole('row')`,
  `getByRole('table')` and `a[href^="/entries/"]` per row all work with no page
  edit at all.
- **QA against the seeded world has a known count**: `status.total_entries`
  comes from the seeded KB, so `SEEDED_ENTRIES.length` plus
  `SEEDED_DAILY_DATES.length` is the number the Total Entries card must show.
  If the number the page shows disagrees with the seed, that is criterion 5 —
  a product or a seed bug, filed, not rounded off with a `toBeVisible`.

### Regimes

- **Zero results** — a query the seeded world cannot match (e.g. a
  `uniqueTitle()`-style string, or a literal no seeded title contains); assert
  the empty state by testid, and that no `a[href^="/entries/"]` is present.
- **More than one match** — `E2E Person` matches all three seeded people;
  assert all three `href`s by id, never `.first()`.
- **A query the KB filter excludes** — with `e2e` selected the seeded entry is
  there; the filter must not be asserted by its option text alone.
- **The skeleton→result transition** — the #9 regime: skeleton present while
  loading, gone when the link appears; never both, never a conditional.
- **QA loading ends** — the spec waits for a stat card, not for the spinner's
  words; a spinner that never ends must fail the test.
- **QA with zero issues** — the seeded world's expected state; assert the
  clean-state element **and** that the Issues heading reads `Issues (0)`, so a
  page that renders neither fails.
- **QA with an issue** — only if the seed produces one. It currently does not;
  do **not** add one (package A's files are out of scope). Report the gap in
  the worker's report so package H or a follow-up can decide.
- **First navigation after server start** — #153's class: a spec failing in
  ~170 ms on run 1 and passing warm is reported against #153, never retried
  around.

### Touches

Existing: `web/e2e/search.spec.ts` (92 lines), `web/e2e/qa.spec.ts` (56 lines);
and, only for `data-testid` / `aria-label` additions as listed above,
`web/src/routes/search/+page.svelte` and `web/src/routes/qa/+page.svelte`.
Possibly `web/src/lib/components/layout/Topbar.svelte` (one testid on the
title) and `web/src/lib/components/common/SkeletonLoader.svelte` (one testid on
the search variant) — both shared components, so a change there must be
additive and named in the report. `CHANGELOG.md`.

New: none.

### Sequence

**After nothing — dispatchable now.** Package F (#160) is merged; the 09-18
"after #49" blocker is dropped, following F's precedent of removing
`toHaveTitle` with a comment naming #49 rather than waiting on it.

The parent flake item is `in_progress`, but that is the umbrella ticket's
status, not an active branch on these files: no open PR and no worktree touches
`web/e2e/search.spec.ts` or `web/e2e/qa.spec.ts`. **G does not wait on it.**

Two real constraints remain:
- **Machine, not files.** `heavy: yes` — Playwright takes two suite slots and
  only one Playwright run happens at a time on this machine. G must not be
  dispatched while another Playwright package is running, even though the file
  footprints are disjoint (that is #104's lesson: port/machine collision is a
  footprint dimension git cannot see).
- **Before package H**, which makes the `e2e` job blocking, and before any
  attempt to *fix* #9 — a fix would touch
  `web/src/routes/search/+page.svelte`, the file this package adds testids to.

### Model, weight, cold read

**Model: sonnet.** Mechanical, with F's two merged spec files as the worked
example, real selectors named above, and acceptance a careful junior engineer
can execute from this ticket alone.

**heavy: yes** — Playwright: two suite slots, one at a time on this machine.

**Cold read: no.** No public shape changes: no CLI, REST, MCP-tool or
file-format surface; no auth, storage or server code. The page edits are
additive `data-testid`/`aria-label` attributes only. The one thing review must
check by eye is that no assertion was *softened* to make a run green — that is
a diff read (grep the branch for `.or(`, `if (` and `text=` in `web/e2e/`), not
a cold read. If the worker's report says it changed anything under
`web/src/lib/stores/` or altered a guard in either page, escalate to a cold
read then.

### Out of scope

- **Root-causing or fixing #9.** Do not touch
  `web/src/lib/stores/search.svelte.ts`, and do not change the
  `{#if searchStore.loading}` / `{#if !searchStore.loading && …}` guards. The
  spike found the symptom unreachable from current source; this package's job
  is the assertion that lets the issue be *closed*, not a fix.
- **Package A's files**: `web/e2e/global-setup.ts`, `web/e2e/fixtures.ts`,
  `web/e2e/ports.ts`, `web/playwright.config.ts`. A missing seed (a QA issue to
  assert on, a second note matching a query) is **reported**, not added.
- **The `e2e` CI job** — package H owns `ci.yml`.
- **#49** (root layout overwrites page titles) — drop the `toHaveTitle`
  assertions with a comment naming #49; do not fix the layout.
- **#153** — report, do not retry around.
- Any other spec file. D, E and F are merged; re-running them is evidence, not
  scope.
- Restyling either page, or "while I'm here" accessibility work beyond the
  `aria-label`s on the four unlabeled selects named above.

## Worker report 2026-09-19

Both specs rewritten, 5/5 + full suite green. The #9 assertion is
`web/e2e/search.spec.ts:44` (`a seeded query renders the seeded entry as a
result link, skeleton gone`), asserting `a[href="/entries/e2e-note-alpha"]`
visible with title text and `getByTestId('search-skeleton')` at count 0 in the
same test — the conductor can close #9 citing this test.

**Correction to this groom's premise (not a product bug):** the "QA with an
issue" regime is marked above as "it currently does not [produce one]" —
false. `global-setup.ts` (Package A, out of scope) creates no links between
any seeded entry (the same fact `graph.spec.ts` already asserts against
`/api/graph` — "the seeded world has no linked entries"), and
`qa_service.py`'s `orphan_entry` rule (line 640) fires for every entry with no
links in either direction. The seeded world therefore reports exactly
`SEEDED_ENTRIES.length + SEEDED_DAILY_DATES.length` = 17 `orphan_entry`
issues (info) plus 20 `rubric_violation` issues (warning) = 37 total, on
every run, deterministically. There is no zero-issue regime to test against
this seed. `qa.spec.ts`'s `QA against the seeded world reports an
orphan_entry issue for every seeded entry` test (line 46) asserts this
invariant instead (total-issues count from the stat card, the Issues(N)
heading matching it, and one `orphan_entry` row per `SEEDED_ENTRIES` id) —
this is now the closest thing to a "QA with an issue" regime this seed can
exercise, and I'd suggest whoever picks up the parent ticket or package H
retire the "QA with zero issues" framing rather than add a seed change to
force it true.

Also found while removing the `.or()` dodge on the mode-selector test:
semantic search against this e2e world returns zero results for every query,
always — `.pyrite/config.yaml` in this worktree sets `auto_embed: false` and
`global-setup.ts` never computes embeddings, so
`SearchService._semantic_search`'s `has_embeddings()` check
(`search_service.py:351`) is always false, and the mode surfaces
`reason: "semantic_empty_no_embeddings"` (`search_service.py:247`). This is an
intentional, named fallback in the product, not a bug — `qa.spec.ts`'s
counterpart in `search.spec.ts` (`mode selector toggles aria-pressed and
keyword/hybrid still return the seeded entry`, line 109) asserts the empty
state for semantic and the keyword-fallback result for hybrid instead of
"still returns the seeded entry" for all three modes, with the reasoning in a
comment at the top of that test.

No real product bug requiring `test.fixme` was found by a newly-real
assertion in this package (the two findings above are groom-premise
corrections and an already-documented product behaviour, not new defects).
