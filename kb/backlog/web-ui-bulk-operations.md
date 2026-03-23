---
id: web-ui-bulk-operations
type: backlog_item
title: "Web UI: Bulk operations on entry lists"
kind: feature
status: proposed
priority: medium
effort: L
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

Users can only act on entries one at a time. Tagging, moving, changing status, or deleting multiple entries requires repetitive individual operations, which is impractical for large knowledge bases.

## Solution

Add multi-select checkboxes to entry list items with a select-all toggle. When entries are selected, show a bulk action toolbar with options to add/remove tags, move to a different KB, change status, and delete. Implement selection state management in the list component and use batch API calls to apply actions efficiently. Include a confirmation dialog for destructive operations.
