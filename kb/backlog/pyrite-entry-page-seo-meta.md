---
id: pyrite-entry-page-seo-meta
type: backlog_item
title: "Full SEO meta tags and JSON-LD on live-app entry pages"
kind: feature
status: proposed
priority: medium
effort: S
tags: [seo, publication, hosting, web]
links:
- target: epic-pyrite-publication-strategy
  relation: subtask_of
  kb: pyrite
- target: pyrite-remove-static-renderer
  relation: unblocks
  kb: pyrite
---

## Problem

The static renderer (`site_cache.py`) emits rich per-page metadata:
`<title>`, `<meta name=description>`, `og:*`, `twitter:*`,
`<link rel=canonical>`, and JSON-LD Article schema with a publisher
field. The live SvelteKit entry page does not yet provide an
equivalent — its `<svelte:head>` may set title but is missing the
rest of the SEO surface.

Once the live app emits complete meta, the static renderer's SEO
value disappears.

## Scope

Audit and complete the `<svelte:head>` block in
`web/src/routes/entries/[id]/+page.svelte` so every entry page ships
crawler-visible metadata:

- `<title>{entry.title} — {kb_name} | {brand.name}</title>`
- `<meta name="description" content="{entry.summary or first 160 chars of body}">`
- `<meta property="og:title" content="{entry.title} — {kb_name}">`
- `<meta property="og:description" content="{entry.summary}">`
- `<meta property="og:type" content="article">`
- `<meta property="og:url" content="{canonical_url}">`
- `<meta property="og:image" content="{brand.og_image_url or favicon}">`
- `<meta name="twitter:card" content="summary">`
- `<meta name="twitter:title" ...>`
- `<meta name="twitter:description" ...>`
- `<link rel="canonical" href="{canonical_url}">`
- `<script type="application/ld+json">{...Article JSON-LD}</script>`
  with:
  - `@type` from the entry-type → schema.org mapping
    (`site_cache.py:_SCHEMA_TYPES` has this; reuse by moving to a
    shared util or expose via API)
  - `datePublished` / `dateModified` from index timestamps
  - `publisher` = `{brand.name}` from the brand store
  - `author` when `created_by` is set

Also apply the same pattern on:
- KB index page (`+page.svelte` at home)
- Per-KB browse page (if one exists)
- Search results page (only `noindex` + title)

The JSON-LD entry-type map needs to be reachable from the
frontend — simplest is to ship it as a static JSON file or bake it
into the build. Doing this in the live app means the frontend
imports the same mapping source as the server.

## TDD

Frontend tests (vitest):
1. `test_entry_page_head_has_og_title` — render entry, check
   `document.head` contains an `og:title` meta tag matching entry.
2. `test_entry_page_head_has_jsonld_publisher` — parse the
   `application/ld+json` script, assert publisher.name equals the
   brand name.
3. `test_entry_page_canonical_link_present` — assert canonical
   `<link>` points at the entry's URL.

SSR/e2e tests (playwright):
4. `test_entry_page_crawler_sees_meta` — fetch with a bot-shaped
   User-Agent, verify meta tags appear in raw HTML before hydration
   (may require adapter-static SSR mode).

## Changes

- `web/src/routes/entries/[id]/+page.svelte` — expanded
  `<svelte:head>` block
- `web/src/lib/utils/seo.ts` (new) — helpers that build meta/JSON-LD
  objects from entry + brand + KB
- `web/src/lib/types/seo.ts` (new) — the entry-type → schema.org map
  (mirrors `pyrite/services/site_cache.py:_SCHEMA_TYPES`)
- `web/src/routes/+page.svelte`, `/[kb]/+page.svelte` (if it exists) —
  apply the same pattern
- Shared util exported via `/config/schema-types` API endpoint or
  baked into the frontend bundle

## Done when

- View-source on an entry page shows full og/twitter/JSON-LD meta
- Using Google's Rich Results Test tool on an entry URL returns
  successful parsing
- Canonical URL matches the route
- Brand name from `/config/branding` surfaces correctly in the
  publisher field

## Depends on

Nothing blocking; [[pyrite-white-labeling]] already shipped so
`brand.name` is available.

## Unblocks

[[pyrite-remove-static-renderer]]
