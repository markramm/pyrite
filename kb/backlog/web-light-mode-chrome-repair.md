---
id: web-light-mode-chrome-repair
type: backlog_item
title: "Web: light mode has invisible text in sidebar chrome + always-dark graph canvas (dark-first blind spots)"
kind: bug
status: proposed
priority: medium
effort: S
created: "2026-07-03"
tags: [web, ux, theming, ux-audit-2026-07]
---

## Problem

Dark is the default theme (`ui.svelte.ts:12`), so light mode ships
untested. Verified dark-hardcoded spots that are broken or jarring
in light mode:

- Sidebar wordmark: `text-zinc-100` with no `dark:` variant —
  white-on-near-white (`Sidebar.svelte:129`).
- Sidebar quick-search input: `text-zinc-300` on `bg-zinc-100`
  (`Sidebar.svelte:151`).
- `EmptyState` title `text-zinc-300` (`common/EmptyState.svelte:19`).
- Welcome block text/buttons (`routes/overview/+page.svelte:56-70`).
- Graph canvas: hardcoded `#09090b` background, dark dot-grid, and
  `#a1a1aa` node labels regardless of theme
  (`GraphView.svelte:119,271-275`) — a black panel in a white page.

## Fix

Add the missing light/dark variants (or route through semantic
tokens — see [[web-brand-tokens-implementation]], which is the
durable fix); make graph colors theme-derived. Add one light-mode
screenshot pass to the e2e suite so dark-first development can't
silently break light again.

## Acceptance criteria

- Every sidebar element legible in both themes.
- Graph canvas follows the active theme.
