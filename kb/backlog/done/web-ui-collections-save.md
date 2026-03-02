---
id: web-ui-collections-save
title: "Wire up collection creation save button"
type: backlog_item
tags:
- bug
- frontend
- web-ui
kind: bug
priority: medium
effort: S
status: done
milestone: "0.13"
links:
- web-ui-review-hardening
---

## Problem

`/collections/new` has a Create button that is disabled with a comment "not yet wired up." The QueryBuilder UI exists and works for building filter criteria, but saving does nothing. This is a dead-end page.

## Solution

Either:
1. Wire the save button to the backend collection creation endpoint (if it exists)
2. Or remove the `/collections/new` route and the "New Collection" link until the backend is ready — don't show users a form they can't submit
