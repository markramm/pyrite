---
id: web-ui-accessibility-fixes
title: "Fix accessibility gaps in web UI components"
type: backlog_item
tags:
- improvement
- frontend
- web-ui
- accessibility
kind: improvement
priority: medium
effort: S
status: proposed
links:
- ux-accessibility-fixes
- web-ui-review-hardening
---

## Problem

Several accessibility issues found in the audit:
- `SplitPane` drag handle not keyboard-accessible (suppressed a11y warning)
- `CommandPalette` and `QuickSwitcher` lack focus traps and `role="dialog"`
- Settings form labels not properly associated (missing `for`/`id`)
- Entry toolbar lacks `role="toolbar"` grouping
- Icon-only buttons have inconsistent `aria-label` vs `title` usage

## Solution

- Add keyboard support to SplitPane (arrow keys to resize)
- Add focus trap and proper ARIA to modal overlays
- Wire up `for`/`id` on Settings form labels
- Add `role="toolbar"` to entry edit toolbar
- Audit all icon buttons for consistent `aria-label`

Subsumes the aria-label items from the original `ux-accessibility-fixes` backlog item.
