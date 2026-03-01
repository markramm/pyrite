---
id: ux-accessibility-fixes
title: "Frontend UX & Accessibility Fixes"
type: backlog_item
tags:
- improvement
- frontend
- accessibility
- ux
- code-hardening
kind: improvement
priority: high
effort: M
status: planned
links:
- roadmap
- web-ui-review-hardening
---

# Frontend UX & Accessibility Fixes

**Wave 7 of 0.9 Code Hardening.** Independent frontend changes for demo-readiness and accessibility. All items can run in parallel.

## Items

| Item | Files | Effort | Description |
|------|-------|--------|-------------|
| Add aria-labels to icon-only buttons | `entries/[id]/+page.svelte`, `entries/+page.svelte` | XS | All icon-only buttons need `aria-label` for screen readers |
| Extract shared typeColors constant | `$lib/constants.ts` (new), `search/+page.svelte`, `GraphView.svelte` | XS | Deduplicate type→color mappings into shared constant |
| Delete dead renderMarkdown function | `entries/[id]/+page.svelte` | XS | Remove unused `renderMarkdown` function |
| Fix entries toolbar mobile overflow | `entries/+page.svelte` | XS | Add `flex-wrap` to prevent toolbar buttons from overflowing on narrow viewports |
| Show entry titles in sidebar recent entries | `Sidebar.svelte`, `entries.svelte.ts` | S | Recent entries in sidebar show titles instead of IDs |
| Standardize HTTP error response format | `endpoints/git_ops.py`, `kbs.py`, `admin.py` | S | Use consistent `{"detail": "..."}` error response format across all endpoints |

## Definition of Done

- All icon-only buttons have descriptive `aria-label` attributes
- `typeColors` imported from single source of truth
- No dead code in entry detail page
- Toolbar wraps cleanly on mobile viewports
- Sidebar recent entries show human-readable titles
- All error responses use `{"detail": "..."}` format
