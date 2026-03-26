---
id: fix-quickswitcher-navigation
title: "Bug: QuickSwitcher uses window.location.href instead of goto()"
type: backlog_item
tags: [frontend, bug, svelte]
kind: bug
priority: high
effort: XS
---

## Problem

`QuickSwitcher.svelte` uses `window.location.href = ...` for navigation, causing a full page reload instead of SvelteKit client-side navigation via `goto()`.

## Fix

Replace `window.location.href` with `goto()` from `$app/navigation`.
