---
id: web-ui-mobile-responsive
title: "Fix mobile responsiveness issues"
type: backlog_item
tags:
- improvement
- frontend
- web-ui
- mobile
kind: improvement
priority: medium
effort: S
status: proposed
links:
- ux-accessibility-fixes
- web-ui-review-hardening
---

## Problem

Several layout issues on mobile viewports:
- Calendar in `/daily` is `hidden md:block` with no fallback — users can't navigate dates on mobile
- Entry detail metadata sidebar (64px fixed) and split pane overflow on small screens
- Entries toolbar buttons overflow on narrow viewports (identified in ux-accessibility-fixes)

## Solution

- Add a compact date picker or inline date nav for mobile daily notes
- Make entry detail metadata collapsible or move to a tab on mobile
- Add `flex-wrap` to entries toolbar
- Test all routes at 360px viewport width
