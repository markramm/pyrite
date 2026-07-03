---
id: web-kb-context-single-authority
type: backlog_item
title: "Web: make KB context explicit and single-authority (URL-first, switcher navigates, persisted)"
kind: bug
status: proposed
priority: high
effort: M
created: "2026-07-03"
tags: [web, ux, navigation, ia, ux-audit-2026-07]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
---

## Problem

The #1 reported new-user confusion ("which KB am I in?") has a
precise cause: FOUR different KB-scoping regimes coexist across
pages, so there is no single answer to the question.

- The store (`src/lib/stores/kbs.svelte.ts:8`) is implicit,
  non-persisted, and defaults to the KB literally named `guide` else
  first-KB (:23-25) — every reload silently resets scope.
- `/entries` and `/orient` use `urlKB ?? kbStore.activeKB`
  (`routes/entries/+page.svelte:33-35`, `orient/+page.svelte:14-15`)
  with no write-back — **on any page reached via `?kb=`, the sidebar
  KB switcher does nothing** (URL wins forever).
- `/search` and `/graph` keep their own local `selectedKb`
  defaulting to all-KBs (`search/+page.svelte:16`,
  `graph/+page.svelte:17`) — the switcher is ignored entirely.
- `/entries/[id]` has no KB dimension at all
  (`entries/[id]/+page.svelte:49`) — cross-KB ID collisions are
  ambiguous and the URL can't express "this entry in that KB".
- `KBSwitcher.svelte` only mutates the store (:34-36 setActive); it
  does not navigate or touch the URL.

## Fix

1. KB context lives in the URL (consistent `?kb=` handled once in a
   layout load, or `/kb/[name]/...` routes — decide once, ADR-worthy).
2. `KBSwitcher` navigates (updates the URL) instead of mutating a
   store; store becomes a derived cache of the URL.
3. Persist last-active KB (localStorage) for the bare-`/` entry only.
4. Extract the precedence logic into ONE tested util — today it's
   inline per page and untested (see
   [[web-test-confusion-surfaces]]).
5. Entry detail URLs carry KB.

## Acceptance criteria

- Switching KB in the sidebar changes scope on EVERY scoped page,
  regardless of how you arrived; URL always answers "which KB".
- Reload preserves KB context.
- One util owns precedence, with unit tests for URL/store/default
  cases.
