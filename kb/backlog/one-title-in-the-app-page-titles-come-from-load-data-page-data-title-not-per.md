---
id: one-title-in-the-app-page-titles-come-from-load-data-page-data-title-not-per
title: 'One <title> in the app: page titles come from load data ($page.data.title), not per-route <svelte:head>'
type: backlog_item
tags:
- web
- quality
- refactor
importance: 5
status: proposed
priority: medium
rank: 0
---

## Problem

Every route declares its own `<svelte:head><title>`, and the root layout supplies a brand-name default — two writers of `document.title` racing by effect order (#49). PR #202's first pass tried to arbitrate the race with navigation hooks and a snapshot of `document.title`; the cold read showed that string-diffing cannot distinguish "the route re-claimed the same title" from "the route claimed nothing" (a same-route `goto` on `/entries` reintroduced the bug). The fix that landed is a `{#if UNTITLED_ROUTES.includes($page.route.id)}` guard in the layout head — correct, three lines, but it carries a hand-kept list.

## Fix

The idiomatic SvelteKit shape: **one** `<svelte:head><title>{$page.data.title ?? brandStore.name}</title></svelte:head>` in the root layout; each route returns `title` from its `+page.ts` `load` (mechanical, ~25 routes, two lines each); the three dynamic-title routes (`entries/[id]`, `collections/[id]`, `orient`) derive it from a store or `$derived` value instead of `load` data. Delete every per-route `<svelte:head><title>` and the `UNTITLED_ROUTES` list. Verified by the #202 cold read against all four #49 regimes (untitled mount, nav to titled, branding resolving on a titled route, nav back to untitled with a custom brand name).

## Acceptance

- `grep -rn "<title" web/src/routes` returns exactly one hit, in `+layout.svelte`.
- A vitest component test (`@testing-library/svelte`) renders the layout with a child route and asserts the four regimes, including a same-route navigation.
- The e2e `toHaveTitle` assertions in `settings`, `qa`, `search` still pass (one Playwright run of those specs).
- No visible title flash on entry open: `entries/[id]` resolves its title synchronously from the store when the entry is already cached.

## Regimes

The four above; a route with no `load` (falls back to the brand); a custom brand name; a failed branding fetch.

**Touches** — existing: `web/src/routes/+layout.svelte`, every `web/src/routes/**/+page.svelte` with a `<title>` (~25) and their `+page.ts` (create where absent), the three dynamic-title routes; new: one component test. **Sequence:** after #202 merges. **Model:** Sonnet (mechanical once the layout line is in). **heavy:** yes (one Playwright run). **Cold read:** no. **Out of scope:** changing any title's wording.
