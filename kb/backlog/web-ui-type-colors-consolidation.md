---
id: web-ui-type-colors-consolidation
title: "Consolidate type colors into single source of truth"
type: backlog_item
tags:
- improvement
- frontend
- web-ui
kind: improvement
priority: high
effort: XS
status: proposed
links:
- ux-accessibility-fixes
- web-ui-review-hardening
---

## Problem

`typeColors` are defined in three places with inconsistent values:
- `$lib/constants.ts` — canonical
- `EntryCard.svelte` — local copy, different values (e.g. `adr` is pink instead of purple)
- `graph/+page.svelte` — another local copy

This means entries show different colors on different pages.

## Solution

Delete the local copies. Import from `$lib/constants.ts` everywhere. This was already identified in the UX accessibility fixes item but hasn't been done.
