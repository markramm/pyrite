---
id: fix-sidebar-derived-bug
title: "Bug: Sidebar calls userInitials() as function but it's a $derived value"
type: backlog_item
tags: [frontend, bug, svelte]
kind: bug
priority: high
effort: XS
---

## Problem

`web/src/lib/components/layout/Sidebar.svelte:186` — `{userInitials()}` calls `userInitials` as a function, but it's declared with `$derived.by(...)` which returns a reactive value, not a function. Should be `{userInitials}` without parentheses.

## Fix

Change `{userInitials()}` to `{userInitials}` in the template.
