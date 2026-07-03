---
id: searchstore-has-no-stale-response-guard-against-overlapping-searches
title: SearchStore has no stale-response guard against overlapping searches
type: backlog_item
tags:
- web
- tech-debt
- search
importance: 5
kind: task
status: proposed
priority: medium
effort: S
rank: 0
---

## Problem

Discovered while investigating web-search-results-never-render (not
the reported bug itself, a separate latent fragility found during
the trace): `SearchStore.execute()`
(`web/src/lib/stores/search.svelte.ts`) has no stale-response guard.
It sets `this.results = res.results` whenever its `api.search()`
promise resolves, with no check that the resolving response still
corresponds to the current query/filters.

`web/src/routes/search/+page.svelte` calls `runSearch()` directly
(bypassing the debounce) from several immediate-trigger handlers:
`setMode()`, `onKbChange()`, `onTypeChange()`, and the advanced-
filter `onchange` handlers. Any of these can race a debounced
`execute()` call still in flight from a recent keystroke. Whichever
request resolves last wins and overwrites `results`/`loading` --
which could show results for a stale query (e.g. a fast typist types
"abc" then "abcdef", the "abc" response arrives after the "abcdef"
one and clobbers it), or a mode/KB/type filter change getting
stomped by an in-flight plain-text search.

## Fix

Add a request-generation guard: increment a counter (or use an
`AbortController`) on each `execute()` call, and only apply the
result if it's still the most recent in-flight request when it
resolves. Standard pattern -- no architectural change needed, just
guard the `results =`/`loading =` assignment in
`SearchStore.execute()`'s resolution path.

## Acceptance criteria

- A new test in `search.test.ts` (or equivalent) that fires two
  `execute()` calls with the second resolving first and the first
  resolving second, asserting the store ends up showing the SECOND
  call's results, not the first's.
- No behavior change for the common case (single in-flight search).
