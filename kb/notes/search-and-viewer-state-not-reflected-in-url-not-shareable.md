---
id: search-and-viewer-state-not-reflected-in-url-not-shareable
title: Search and viewer state not reflected in URL (not shareable)
type: backlog_item
tags:
- enhancement
- web
- search
- ux
importance: 5
kind: feature
status: completed
priority: high
effort: M
rank: 0
---

## Problem

Two separate issues with the same root cause:

### Web app search (/search)
The search page reads ?q= and ?mode= on mount but never writes back to the URL via pushState/replaceState. If a user types a query then copies the URL, it won't include the query. Advanced filters (date, tag, type) are also not reflected in URL.

### Cascade viewer
Search terms, sort order, page number, and tag filters are not in the URL. All state is lost on back navigation. Someone sharing a filtered view of all DOGE events can't do it.

## Fix

For the web app search page: use replaceState to sync all search state (query, mode, type, tag, date range) to URL params. Read all params on mount.

For the viewer: same pattern -- persist search, sort, page, and filters as URL query params.

## Scope

Pyrite-general (web app search). Plus cascade viewer.
