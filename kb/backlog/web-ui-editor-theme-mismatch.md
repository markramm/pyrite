---
id: web-ui-editor-theme-mismatch
type: backlog_item
title: "Bug: Editor does not respect light/dark mode toggle"
kind: bug
status: proposed
priority: medium
effort: S
tags: [web, bug, editor, theme]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

The CodeMirror editor always renders with a dark theme regardless of the current light/dark mode setting. When the page is in light mode, the editor area has a dark background with light text while the surrounding toolbar and sidebar are light. The theme mismatch is jarring.

## Root cause

In `web/src/lib/editor/codemirror/setup.ts`, `createEditorExtensions` receives `dark: uiStore.theme === 'dark'` and selects `darkTheme` or `lightTheme`. But the Editor component in `Editor.svelte` only creates the view once in `onMount`/`$effect` — when the theme toggles, the editor isn't recreated with the new theme.

Additionally, the `uiStore.theme` value may not be read reactively when creating extensions.

## Fix

Either recreate the CodeMirror view when theme changes, or use a dynamic theme compartment that can be reconfigured without destroying the view.
