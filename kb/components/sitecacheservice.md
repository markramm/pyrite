---
id: sitecacheservice
title: SiteCacheService
type: component
tags:
- core
- site-cache
- seo
kind: service
path: pyrite/services/site_cache.py
owner: markr
dependencies:
- kb_service
- template_service
---

Pre-renders KB entries to static HTML files for SEO-friendly serving at /site/. Supports custom homepages, progressive JS, JSON-LD, sitemaps.
