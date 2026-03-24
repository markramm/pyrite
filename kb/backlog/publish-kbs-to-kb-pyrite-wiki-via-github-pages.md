---
id: publish-kbs-to-kb-pyrite-wiki-via-github-pages
title: Publish KBs to kb.pyrite.wiki via SSR public site
type: backlog_item
tags:
- publishing
- seo
- ssr
- web
kind: feature
effort: L
status: proposed
priority: high
links:
- target: ssr-public-site
  relation: designed_by
  kb: pyrite
---

## Problem

Pyrite KBs are rendered client-side in the app SPA, making content invisible to search crawlers. Over 5,000 entries across 27 lean/agile/systems thinking KBs are ready to publish but lack a crawlable interface. The capturecascade.org site has proven that structured, crawlable KB content generates strong organic search traffic.

## Revised approach (supersedes Quartz/GitHub Pages plan)

Instead of exporting to static sites, run the **same Pyrite app with SSR** at kb.pyrite.wiki. Same codebase, same data, same server — just a read-only, content-forward route group with server-side rendering for SEO.

See [[ssr-public-site]] for the full design doc.

### Architecture

One SvelteKit app, two route groups:
- `/app/...` — Full Pyrite UI (auth, editing, settings)
- `/site/...` — Public read-only view (SSR, SEO metadata, content-forward)

Caddy maps `demo.pyrite.wiki` -> `/app`, `kb.pyrite.wiki` -> `/site`.

### Why not Quartz

- Cross-KB wikilinks (`[[boyd:ooda-loop]]` from Deming KB) don't work in Quartz — each KB is an isolated site
- Pyrite's search (keyword + semantic) works out of the box, no static search index needed
- Typed entries can render with type-appropriate metadata, not generic wiki pages
- One codebase to maintain, not a build pipeline per KB

### URLs

- `kb.pyrite.wiki/deming/` — Deming KB overview
- `kb.pyrite.wiki/deming/system-of-profound-knowledge` — Entry page
- `kb.pyrite.wiki/boyd/ooda-loop` — Cross-KB link resolves natively

### Excluded from public publishing

- pyrite (internal project KB), drafts, kb-ideas, personal KBs

## Acceptance Criteria

- [ ] SvelteKit route group split: `(app)/` and `(site)/`
- [ ] adapter-node SSR for `/site` routes
- [ ] Per-entry SEO: title, meta description, Open Graph, JSON-LD
- [ ] `sitemap.xml` generated from entry index
- [ ] Cross-KB wikilinks resolve within `/site`
- [ ] At least 5 KBs crawlable at kb.pyrite.wiki
- [ ] Google Search Console confirms indexing
- [ ] "Edit on Pyrite" links point to demo.pyrite.wiki

## Strategic Context

1. **SEO / discoverability**: 5,000+ pages of structured content with cross-references generate organic search traffic
2. **Pyrite demo**: Each published KB is a live demonstration of what Pyrite produces
3. **Reference resource**: RRE (2,525 entries), Boyd (109), Deming (96) would become the largest public resources on their subjects

## Notes

- The RRE (Agre) KB index page should explicitly connect 'Philip Agre' to the Red Rock Eater newsletter name for search discoverability
- JSON-LD structured data should map entry types to schema.org (note->Article, person->Person, organization->Organization, event->Event, source->ScholarlyArticle)
- Pagefind could supplement Pyrite's search as a zero-JS fallback, but not required for MVP
