---
id: bug-frontmatter-type-field-leaks-into-rendered-body-on-site-cache-pages
title: 'Bug: Frontmatter type field leaks into rendered body on site cache pages'
type: backlog_item
tags:
- bug
- site-cache
- export
- critical
importance: 5
kind: bug
status: todo
priority: critical
effort: S
rank: 0
---

## Problem

Every event page on capturecascade.org starts with 'type: timeline_event' rendered as visible text. This pollutes:
- Every event page body
- Every og:description meta tag
- Every JSON-LD structured data description
- Global search API snippets

## Root Cause

The site cache export/render step is including the frontmatter type field in the body output. The body content starts with the raw YAML field instead of the actual event description.

## Fix

Trace the site cache render pipeline. The body should be stripped of any frontmatter fields before rendering. Check the export service, site cache builder, and/or the markdown-to-HTML renderer.

## Impact

Affects all 4,529 event pages. Fixing this single issue improves appearance of every page and every social share.

## Scope

Pyrite-general: affects any site cache deployment, not just Cascade.
