---
id: pyrite-dynamic-sitemap
title: "Dynamic /sitemap.xml and /robots.txt for SEO"
type: backlog_item
tags: [seo, publication, hosting, web]
links:
- target: epic-pyrite-publication-strategy
  relation: subtask_of
  kb: pyrite
- target: pyrite-remove-static-renderer
  relation: unblocks
  kb: pyrite
importance: 5
kind: feature
status: completed
priority: medium
effort: S
rank: 0
---

**Implementation note (as shipped):** this ticket references a
`pyrite-kb-publication-flag` as the eventual clean signal for "which
KBs are public." That ticket was subsequently dropped — the existing
`KBConfig.default_role == "read"` field already serves this purpose
across the permissions system and the sitemap, so no new flag was
added. The sitemap service filters on `default_role == "read"`.

## Problem

The live SvelteKit app is a client-rendered SPA. Crawlers in 2026 can
execute JS, but SEO indexing still works best when a server-generated
sitemap enumerates indexable URLs with freshness hints. Today Pyrite
has no sitemap — discoverability depends on the static renderer
(`site_cache.py`) producing crawler-visible HTML files at `/site/*`.

If we generate a proper sitemap plus good `<svelte:head>` metadata in
the live app (see [[pyrite-entry-page-seo-meta]]), the static
renderer's SEO role disappears.

## Scope

Add two public endpoints to the server:

### `GET /sitemap.xml`

Returns an XML sitemap enumerating indexable entries across
published KBs. For each entry:
- `<loc>` — canonical URL on the live app (e.g.
  `https://{host}/entries/{kb}/{entry_id}`)
- `<lastmod>` — from the entry's `updated_at` in the index
- `<changefreq>` — `weekly` default; `monthly` for entries whose
  lifecycle is `archived`
- `<priority>` — 0.8 for landing + KB index pages, 0.6 default,
  0.4 for archived

Only include:
- Entries in KBs where `kb.yaml: published: true` AND the operator
  has marked them indexable (as shipped: filtered on
  `KBConfig.default_role == "read"` — see the implementation note
  above)
- Non-archived or `lifecycle != retired`
- Entries whose access default is `read` (public)

Large KBs: split into sitemap-index format
(`<sitemapindex>` at `/sitemap.xml`, individual per-KB sitemaps at
`/sitemap/{kb}.xml`) when total entry count exceeds ~10,000.

### `GET /robots.txt`

Returns:
```
User-agent: *
Allow: /
Sitemap: {site_url}/sitemap.xml
```

`{site_url}` comes from `branding.yaml: site_url` when configured;
otherwise built from the request's `Host` header.

Private KBs are excluded from the allow list via `Disallow:` lines
per-KB when access control is configured.

## TDD

1. `test_sitemap_xml_enumerates_published_entries` — fixture KB with
   3 entries marked published, assert all 3 appear in the XML with
   correct `<loc>` values.
2. `test_sitemap_excludes_private_kbs` — a KB without
   `published: true` is not in the sitemap.
3. `test_sitemap_lastmod_reflects_updated_at` — modify an entry,
   assert its `<lastmod>` changes.
4. `test_robots_txt_points_at_sitemap` — GET `/robots.txt` contains
   a `Sitemap:` line.
5. `test_robots_txt_uses_branding_site_url_when_set` — with a
   branding folder providing `site_url`, that URL appears in the
   `Sitemap:` line.

## Changes

- `pyrite/server/endpoints/seo.py` (new) — the two endpoints, mounted
  OUTSIDE `/api` (crawlers don't auth). Mirror the branding-endpoints
  mounting pattern.
- `pyrite/services/sitemap_service.py` (new) — query logic,
  pagination, sitemap-index split
- Add a cache-control header; sitemaps can be cached for ~1 hour.
- `docs/deployment/seo.md` (new) — operator guide: where the
  sitemap lives, when to flush CDN caches, how `published:` interacts.

## Done when

- `curl $host/sitemap.xml` returns valid XML validated against
  https://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd
- `curl $host/robots.txt` returns a valid robots.txt with sitemap
  pointer
- Private/unpublished entries are absent from the sitemap
- Large-KB split into sitemap-index works for a fixture with
  11,000 entries

## Depends on

As shipped: uses `KBConfig.default_role == "read"` as the publication
signal (see implementation note at top). The originally-proposed
`pyrite-kb-publication-flag` ticket was dropped as redundant.

## Unblocks

[[pyrite-remove-static-renderer]]
