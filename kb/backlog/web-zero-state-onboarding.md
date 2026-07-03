---
id: web-zero-state-onboarding
type: backlog_item
title: "Web: real zero-state path — create a KB in-app, no CLI punts, landing page doesn't dead-end"
kind: improvement
status: proposed
priority: medium
effort: M
created: "2026-07-03"
tags: [web, ux, onboarding, ux-audit-2026-07]
links:
- target: docs-onboarding-fiction-sweep
  relation: related
  kb: pyrite
---

## Problem

The first-run experience is one conditional block on `/overview`
(`routes/overview/+page.svelte:50-71`), and the path to it is broken:

- A brand-new user landing on `/` sees the hero plus "No knowledge
  bases available." (`routes/+page.svelte:72`) with NO action — a
  dead end. `/` does not redirect to the welcome state.
- With zero KBs, "Create First Entry" leads to a form whose KB
  selector has nothing to select; the empty-KB message elsewhere
  says "Run `pyrite kb add`" (`overview:221`) — punting web users to
  the CLI. No in-app create-KB path exists outside `/settings/kbs`.
- Nothing explains what a KB is, why the default KB is named
  `guide` (`kbs.svelte.ts:24`), or what the nav destinations mean.
  The guide-KB-as-onboarding idea exists but nothing points at it.
- The welcome block itself is dark-hardcoded (`overview:56-70`) —
  see [[web-light-mode-chrome-repair]].

## Fix

1. Zero-KB state (landing AND overview): one primary action —
   "Create a knowledge base" — in-app, not CLI instructions.
2. Zero-entry state: keep the existing welcome, add "Open the guide"
   pointing at the guide KB explicitly.
3. `/` redirects to the welcome/overview when the instance is empty.
4. Empty states across pages use the existing `EmptyState` component
   (`common/EmptyState.svelte`) with a directing action, per the
   design rule "an empty screen is an invitation to act" — today
   overview, comments, and landing each roll their own, some
   dead-ending.

## Acceptance criteria

- A user on a fresh instance can reach "created a KB, created an
  entry, found it in search" without touching the CLI.
- No empty state anywhere renders text without an action.
