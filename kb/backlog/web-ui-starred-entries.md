---
id: web-ui-starred-entries
title: "Wire up starred entries in sidebar"
type: backlog_item
tags:
- feature
- frontend
- web-ui
kind: feature
priority: medium
effort: S
status: proposed
links:
- web-ui-review-hardening
---

## Problem

`StarButton.svelte`, `StarredSidebar.svelte`, and the `starred` store are built but not surfaced anywhere in the UI. Users can't star entries or see their starred list.

## Solution

- Add `StarButton` to entry detail page (toolbar or metadata panel)
- Add a "Starred" section to the sidebar (collapsible, below recent entries)
- Or remove the components if starring isn't shipping in 0.12
