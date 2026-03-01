---
id: web-ui-review-hardening
title: "Pre-Launch Web UI Review"
type: backlog_item
tags:
- quality
- frontend
- web-ui
- hardening
- launch
kind: improvement
priority: high
effort: S
status: proposed
links:
- ux-accessibility-fixes
- playwright-integration-tests
- demo-site-deployment
- web-ui-logout-button
- web-ui-version-history-fix
- web-ui-type-colors-consolidation
- web-ui-page-titles
- web-ui-loading-states
- web-ui-starred-entries
- web-ui-first-run-experience
- web-ui-mobile-responsive
- web-ui-accessibility-fixes
- web-ui-dead-code-cleanup
---

## Purpose

Final pre-launch review gate. By the time this runs, the individual fix items should already be done. This is the walk-every-route, screenshot-every-state, test-every-browser pass that confirms the UI is demo-ready.

## Checklist

- [ ] Walk every route in Chrome, Firefox, Safari — no console errors
- [ ] Walk every route on mobile viewport (360px) — no layout breaks
- [ ] Walk every route with empty KB — no blank/broken states
- [ ] Walk every route with API down — error states render, no crashes
- [ ] Light and dark mode consistent across all pages
- [ ] All individual fix items verified closed
- [ ] Screenshots captured for launch materials

## When to Run

After all linked fix items are done, before the demo site goes public.
