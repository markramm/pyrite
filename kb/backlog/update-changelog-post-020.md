---
id: update-changelog-post-020
type: backlog_item
title: "Document 43 post-0.20.0 commits in CHANGELOG"
kind: enhancement
status: proposed
priority: high
effort: M
tags: [docs, release, changelog]
epic: epic-release-readiness-review
---

## Problem

43 commits since the 0.20.0 release (2026-03-23) include substantial features that are undocumented:
- SSR public site at /site with SEO metadata and sitemap
- Site cache service (Python-served static HTML)
- Custom homepage support with _homepage entries
- /site/search page with live API-backed search
- Multi-site VPS hosting with shared Docker network + Caddy
- SPA index.html no-cache headers
- Various deployment fixes

## Fix

Add a new CHANGELOG section for these features. Structure by theme (site rendering, deployment, bug fixes) rather than individual commits.
