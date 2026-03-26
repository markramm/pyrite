---
id: add-accessibility-labels
title: "Add missing ARIA labels to frontend components"
type: backlog_item
tags: [frontend, accessibility]
kind: bug
status: done
effort: S
---

## Problem

Several frontend components lack accessibility attributes:
- KBSwitcher `<select>` has no `<label>` or `aria-label`
- ThemeToggle button has no `aria-label`
- Sidebar toggle button missing `aria-expanded`
- EmptyState/ErrorState text colors hardcoded for dark mode (poor contrast in light)
- Graph view completely inaccessible to keyboard/screen readers

## Fix

Add `aria-label` to KBSwitcher, ThemeToggle. Add `aria-expanded` to sidebar toggle. Add `dark:` variants to EmptyState/ErrorState. Add alt text representation for graph view.
