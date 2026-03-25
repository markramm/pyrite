---
id: fix-quickswitcher-navigation
type: backlog_item
title: "Bug: QuickSwitcher uses window.location.href instead of goto()"
kind: bug
status: proposed
priority: medium
effort: XS
tags: [frontend, bug, svelte]
epic: epic-release-readiness-review
---

## Problem

`QuickSwitcher.svelte` uses `window.location.href = ...` for navigation, causing a full page reload instead of SvelteKit client-side navigation via `goto()`.

## Fix

Replace `window.location.href` with `goto()` from `$app/navigation`.
