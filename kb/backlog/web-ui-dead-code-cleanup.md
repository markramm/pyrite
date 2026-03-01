---
id: web-ui-dead-code-cleanup
title: "Clean up unused components and fix style inconsistencies"
type: backlog_item
tags:
- improvement
- frontend
- web-ui
- code-quality
kind: improvement
priority: low
effort: XS
status: proposed
links:
- web-ui-review-hardening
---

## Problem

Several components exist but aren't wired up, and there are minor style inconsistencies:
- `ai/SearchResults.svelte` — exists but not referenced anywhere
- `TagTree.svelte` — built but not used in any route
- `entries/clip/+page.svelte` uses `gray-` Tailwind classes instead of `zinc-`
- `starred` store uses a composable function pattern while all other stores use class singletons
- `renderMarkdown` function in entry detail is dead code (identified in ux-accessibility-fixes)

## Solution

- Delete or defer unused components (SearchResults, TagTree) — or wire them up if they're needed
- Fix `gray-` → `zinc-` in clip page
- Align `starred` store to class pattern or document why it's different
- Delete dead `renderMarkdown` function
