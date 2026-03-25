---
id: fix-sidebar-derived-bug
type: backlog_item
title: "Bug: Sidebar calls userInitials() as function but it's a $derived value"
kind: bug
status: proposed
priority: medium
effort: XS
tags: [frontend, bug, svelte]
epic: epic-release-readiness-review
---

## Problem

`web/src/lib/components/layout/Sidebar.svelte:186` — `{userInitials()}` calls `userInitials` as a function, but it's declared with `$derived.by(...)` which returns a reactive value, not a function. Should be `{userInitials}` without parentheses.

## Fix

Change `{userInitials()}` to `{userInitials}` in the template.
