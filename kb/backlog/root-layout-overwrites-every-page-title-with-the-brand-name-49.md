---
id: root-layout-overwrites-every-page-title-with-the-brand-name-49
title: Root layout overwrites every page title with the brand name (#49)
type: backlog_item
tags:
- bug
- web
importance: 5
status: in_progress
priority: medium
rank: 0
assignee: agent:pyrite-worker
---

Found while building the deterministic Playwright world (Package A of the `playwright-e2e-suite-non-deterministic-failures-*` ticket).

## What happens

`web/src/routes/+layout.svelte` sets `document.title` from the branding store:

```js
// Push branding into the DOM as it loads:
//   --brand-primary      — accent color referenced by chrome components
//   document.title       — replace app.html's static "Pyrite"
$effect(() => {
    if (typeof document === 'undefined') return;
    document.documentElement.style.setProperty('--brand-primary', brandStore.primary_color);
    if (brandStore.loaded) {
        document.title = brandStore.name;
    }
});
```

Every route also declares its own title, e.g. `web/src/routes/search/+page.svelte`:

```svelte
<svelte:head><title>Search — Pyrite</title></svelte:head>
```

The layout effect runs once `brandStore.loaded` flips and clobbers whatever the page set. SSR is off (`+layout.ts`: `export const ssr = false`), so the page title is only ever applied client-side — after which the layout overwrites it.

## Evidence

Probe navigating to every top-level route with a 1.5 s settle, reading `page.title()`:

```
ROUTE /            -> "Pyrite"
ROUTE /entries     -> "Pyrite"     (page declares "Entries — Pyrite")
ROUTE /search      -> "Pyrite"     (page declares "Search — Pyrite")
ROUTE /settings    -> "Pyrite"     (page declares "Settings — Pyrite")
ROUTE /qa          -> "Pyrite"     (page declares "QA Dashboard — Pyrite")
ROUTE /daily       -> "Pyrite"     (page declares "Daily Notes — Pyrite")
ROUTE /timeline    -> "Pyrite"
ROUTE /graph       -> "Pyrite"
ROUTE /collections -> "Pyrite"
ROUTE /login       -> "Pyrite"
```

No route wins. This is a user-visible bug, not only a test one: every browser tab, every bookmark and every window-switcher entry reads "Pyrite" regardless of where you are in the app.

It is also a source of moving e2e failures, because it is a race: `settings.spec.ts:4` and `search.spec.ts:4` failed their `toHaveTitle` in all five of five consecutive runs, while `qa.spec.ts:4` and `daily.spec.ts:4` — the same assertion, same cause — failed in four of five. Whether the page title or the branding effect lands last depends on when `/config/branding` returns.

## Suggested fix

The layout should supply a default, not an override — e.g. put the brand name in `<svelte:head><title>` in the layout (SvelteKit lets a page's head override a layout's) instead of assigning `document.title` in an effect. If a branded suffix is wanted on every page, compose it where the page title is set rather than replacing it wholesale.

## Why not fixed here

Out of scope for Package A (the e2e environment); the pages and their specs belong to packages B/G of that ticket, and this is a product bug in the layout rather than a test-harness one. Filed per ADR-0033.

---
## Groom 2026-09-18 (serial)

Theme **"a route's page title survives the layout"** — closes #49 alone (tick 6 paired it with #45; after #168 they are separate, #45 later).

**Acceptance** (from the issue): a route's own `<svelte:head><title>` survives once `brandStore.loaded` flips; the brand name is the title only where a route declares none. Test form: the issue's probe table, inverted — `/entries`, `/search`, `/settings`, `/qa`, `/daily` each end with the title their page declares; a route with no `<title>` ends with `brandStore.name`.

**Regimes:** branding loads **after** the page title is set (today's clobber) and **before** it (the other half of the race — the issue's 4-of-5 rows); client-side navigation from a titled route to an untitled one (the old title must not stick) and back; a custom brand name (not "Pyrite") — the fallback uses it; branding fetch fails (title stays the static one, no exception in the effect).
**Touches** — existing: `web/src/routes/+layout.svelte` (:116–121, the `$effect` that assigns `document.title`). New: a vitest unit test under `web/src/`. **No Playwright in this theme**: `qa.spec.ts:8`, `search.spec.ts:8` and `settings.spec.ts:22` already hold the `toHaveTitle` assertions; package G (next) runs them.
**Sequence:** after #159's fix merges, so this `fix:` commit can carry its `web/**/*.test.ts` test through the commit-msg hook. Before Playwright package G, whose two specs open with a `toHaveTitle` that #49 fails 5/5 and 4/5.
**Model:** sonnet. **heavy:** no — `npm run test:unit` only (no build, no browsers). **Cold read:** no. **Size:** S, ~80 lines.
**Out of scope:** routes hardcoding "— Pyrite" instead of the brand name (file it); #45; any spec edit.

_Serial order and what is blocked: `kb/notes/serial-queue-2026-09-18.md` on `kb/conductor-log-2026-W38`. One Pyrite task at a time (#168)._

## Triage 2026-09-20

**State: ready.** The `## Groom 2026-09-18` comment above is still correct. Re-verified on `dev` @130f433 — `web/src/routes/+layout.svelte:116-121` still assigns `document.title = brandStore.name` inside the `$effect`, and no route's `<svelte:head><title>` survives it.

**Two sequencing lines corrected:**

- The groom said "after #159's fix merges, so this `fix:` commit can carry its `web/**/*.test.ts` test through the commit-msg hook". **#163 merged 2026-09-19** ("ci: parity — extensions linted, fix-needs-a-test enforced on PRs"), which is that work. Dependency discharged.
- "Before Playwright package G, whose two specs open with a `toHaveTitle` that #49 fails 5/5 and 4/5." Package G is **PR #191, open and awaiting review**. So this is now *late*: G's `qa.spec.ts` and `settings.spec.ts` title assertions will fail on `dev` until this lands. **Dispatch this one early** — it is S, sonnet, ~80 lines, no browser — or expect G to be held on a failure that is not G's.

Everything else stands: acceptance (a route's own `<svelte:head><title>` survives once `brandStore.loaded` flips; the brand name is the title only where a route declares none; test form is the issue's probe table inverted); the regimes (branding loads after **and** before the page title — both halves of the race; client-side nav from a titled route to an untitled one and back; a custom brand name; a failed branding fetch leaves the static title and throws nothing); touches `web/src/routes/+layout.svelte` only, plus a new vitest unit test — **no Playwright in this theme**; **sonnet / heavy: no** (`npm run test:unit` only) **/ cold read: no**.
