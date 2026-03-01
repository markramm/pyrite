---
id: web-ui-logout-button
title: "Add logout button and user menu to sidebar"
type: backlog_item
tags:
- bug
- frontend
- web-ui
- auth
kind: bug
priority: high
effort: XS
status: proposed
links:
- web-ui-auth
- web-ui-review-hardening
---

## Problem

Users can log in but there's no way to log out. `authStore.logout()` exists but no UI element triggers it. The sidebar has no user indicator at all — you can't tell who you're logged in as.

## Solution

Add a user menu to the sidebar footer showing:
- Username / display name
- Role badge (admin/write/read)
- Logout button

When auth is disabled, hide the user menu entirely.
