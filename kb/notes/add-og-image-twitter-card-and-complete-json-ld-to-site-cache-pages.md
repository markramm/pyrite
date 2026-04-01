---
id: add-og-image-twitter-card-and-complete-json-ld-to-site-cache-pages
title: Add og:image, twitter:card, and complete JSON-LD to site cache pages
type: backlog_item
tags:
- enhancement
- site-cache
- seo
- social
importance: 5
kind: feature
status: todo
priority: medium
effort: M
rank: 0
---

## Problem

Site cache pages have incomplete social sharing metadata:
1. No og:image on any event page — social media shares show no preview image
2. No twitter:card, twitter:title, twitter:description meta tags
3. JSON-LD has article title and date but no author, publisher, or URL field
4. og:description is polluted by the frontmatter type leak (separate bug)

## Solution

1. Generate simple OG images per event (dark background, gold text with title and date, site branding)
2. Add twitter:card=summary_large_image meta tags
3. Complete JSON-LD with author, publisher name, datePublished, url
4. Add a site-level default og:image for pages without one

Could use a serverless OG image generator (satori/resvg) or pre-generate during site cache build.

## Scope

Pyrite-general — all site cache deployments benefit from proper social metadata.
