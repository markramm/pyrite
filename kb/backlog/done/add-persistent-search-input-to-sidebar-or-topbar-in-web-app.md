---
id: add-persistent-search-input-to-sidebar-or-topbar-in-web-app
title: Add persistent search input to sidebar or topbar in web app
type: backlog_item
tags:
- enhancement
- web
- search
- ux
importance: 5
kind: feature
status: completed
priority: medium
effort: S
rank: 0
---

## Problem

The web app sidebar has a 'Search' nav link but no persistent search input. Users must navigate to /search or know the Cmd+O shortcut. A search input in the topbar or sidebar would be a significant usability improvement.

Also: the homepage search box on capturecascade.org is non-functional — typing and pressing Enter does nothing.

## Solution

1. Add a search input to the sidebar (above nav links) or topbar
2. On Enter, navigate to /search?q=...
3. Fix the cascade homepage search box to actually navigate to /site/search?q=...

## Scope

Pyrite-general (web app sidebar search). Cascade-specific (homepage search).
