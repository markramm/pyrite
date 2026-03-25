---
id: web-ui-editor-blank-content-bug
title: "Bug: Editor shows blank content when switching to edit mode"
type: backlog_item
tags: [web, bug, editor]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
kind: bug
status: completed
priority: high
effort: S
---

## Problem

When clicking "Edit" on an entry detail page, the CodeMirror source editor shows line numbers (1-28) but no content. The body text is not passed to the editor component despite `editorContent` being set in `toggleEdit()`.

Additionally, the Edit button is visible to anonymous/read-only users on the demo site. Clicking Edit shows a blank editor, and saving would fail with 403. The Edit button should be hidden when the user lacks write permissions.

## Reproduction

1. Go to https://demo.pyrite.wiki/entries/what-is-pyrite
2. Click "Edit" button
3. Editor shows line numbers but no text content

## Investigation notes

- `toggleEdit()` in `entries/[id]/+page.svelte` (line 135-140) sets `editorContent = entryStore.current.body ?? ''`
- The `$effect` on line 55 also sets `editorContent` when entry loads
- The Editor component receives `content` prop — need to check if CodeMirror is initializing before the prop is set
- May be a Svelte 5 reactivity timing issue between state update and component render

## Fix should include

1. Debug why CodeMirror editor receives empty content
2. Hide Edit/Save buttons for anonymous/read-only users
3. Verify TipTap rich text editor has the same issue
