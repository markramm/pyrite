---
id: web-search-results-never-render
title: "Web: search results never render — header says '20 results', list shows skeleton bars forever (API returns data fine)"
type: backlog_item
tags: [web, search, bug, ux-audit-2026-07]
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
importance: 5
kind: bug
status: proposed
priority: high
effort: S
rank: 0
---

## Problem

Reproduced on demo.pyrite.wiki 2026-07-03 (1440x900, both via
`/search?q=` navigation and live typing): the results header renders
("20 results") but the result list shows skeleton placeholder bars
permanently (>6s after networkidle). The API is healthy --
`GET /api/search?q=OODA+loop&mode=keyword` returns 20 well-formed
results with `<mark>` highlights, kb_name, entry_type, importance.
Two console 401s fire on page load (possibly related -- an
auth-gated request the anonymous demo session can't satisfy blocking
the render path?).

Search is the flagship flow; a first-time user (or invited pilot
peer) hits this within minutes and concludes the product is broken.
Screenshots: scratchpad ux-audit/30-search-results-after-wait.png,
33.

## Investigation (2026-07-04) -- could not reproduce

Traced the full render path (`web/src/routes/search/+page.svelte`,
`web/src/lib/stores/search.svelte.ts`, `web/src/lib/api/client.ts`)
and the two console 401s to their actual source:

- The header (line ~257) and the results branch (line ~383) of
  `+page.svelte` both read the exact same `searchStore.loading` /
  `searchStore.results` fields from one flat `{#if}/{:else if}`
  chain -- they cannot legitimately disagree within a render, ruling
  out "header updates, body doesn't."
- `SearchStore.execute()` wraps the API call in `try/catch/finally`;
  `loading` unconditionally clears in `finally` regardless of
  success or failure. Confirmed via `grep` that no other file writes
  `searchStore.loading` -- nothing external can leave it stuck.
- The two console 401s are real but traced to a confirmed, harmless,
  unrelated source: `web/src/lib/stores/auth.svelte.ts`'s
  `authStore.init()` and `Sidebar.svelte`'s own independent
  `onMount` **both** call `api.getMe()` against `/auth/me` for the
  anonymous session -- duplicate/redundant, not a refactor
  regression, but each is independently `try/catch`-guarded and
  writes only to its own isolated state. Neither touches
  `searchStore`.
- There is no global fetch wrapper, no `hooks.client.ts`, and no
  shared "global error" store anywhere in `web/src/` that could let
  one request's 401 suppress an unrelated component's render.
- Live-verified against `demo.pyrite.wiki/search` (anonymous
  session, no cookies) with three separate repro attempts (direct
  `?q=` URL, character-by-character typing, and a rapid 4-keystroke
  debounce-race) -- all three rendered correctly: skeleton cleared,
  "20 results" header, full result list with `<mark>` highlights.

**Not closing this ticket** -- a real screenshot-documented repro
exists (see scratchpad ux-audit files referenced above), so either
(a) it's a transient/environment-specific condition (stale cached
JS bundle mismatched with a newer/older API shape would produce
exactly this symptom -- header from one code version, body decision
from another -- and wouldn't show up in a source-only trace), or (b)
the repro conditions differ from what was tried here (different
browser/session state/exact click sequence). Re-open with the
active investigation once a fresh, reproducible repro is available
-- ideally the two exact 401 request URLs from the browser network
tab (not `/auth/me`, which has been ruled out), and confirmation of
which built JS bundle was actually served during the repro.

**Also filed as a separate latent-fragility finding** (not the
reported bug, but discovered during this trace and worth its own
ticket): `SearchStore.execute()` has no stale-response guard -- no
query-token/AbortController check that a resolving response still
matches the current query. `+page.svelte` calls `runSearch()`
directly (bypassing the debounce) from `setMode()`, `onKbChange()`,
`onTypeChange()`, and advanced-filter `onchange` handlers, any of
which can race a debounced `execute()` from typing -- last response
to resolve wins, which could show stale/wrong results for a fast
typist or rapid filter-clicker. See
[[searchstore-has-no-stale-response-guard-against-overlapping-searches]].

## Fix

Root-cause the render stall (skeleton state never cleared --
suspect: the component awaits a second request that 401s for
anonymous users, or a store update never resolves). Fix, and make
the failure mode honest: if any part of result hydration fails,
show the results we have or an error, never permanent skeletons.
Check whether this reproduces locally with auth (may be
demo/anonymous-specific -- which is exactly the pilot peer's first-
session condition).

## Acceptance criteria

- Anonymous demo user sees rendered results.
- e2e search spec asserts result text content (not just container
  presence), gated in CI per [[web-test-confusion-surfaces]].
- Zero console 401s on the search page for a read-authorized user.
