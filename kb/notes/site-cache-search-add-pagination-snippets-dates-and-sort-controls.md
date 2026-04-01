---
id: site-cache-search-add-pagination-snippets-dates-and-sort-controls
title: 'Site cache search: add pagination, snippets, dates, and sort controls'
type: backlog_item
tags:
- enhancement
- site-cache
- search
- ux
importance: 5
kind: feature
status: todo
priority: medium
effort: M
rank: 0
---

## Problem

The site cache search page (/site/search) has several gaps:
1. Hard cap at 50 results with no pagination
2. No snippet/excerpt showing why a result matched
3. No date shown on results (critical for a timeline project)
4. No sort controls (not chronological, not alphabetical)
5. No tag display on results
6. Two disconnected search systems (site search vs viewer search) with different behavior

## Solution

1. Add pagination or infinite scroll
2. Include snippet/excerpt in results (the search API likely returns these)
3. Show date and tags on each result
4. Add sort dropdown (relevance, date asc/desc)
5. Consider unifying the two search experiences or cross-linking them

## Scope

Pyrite-general (site cache search is a core feature).
