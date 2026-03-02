---
id: web-ui-sidebar-auth-error-handling
title: "Add Error Handling to Sidebar Auth Check"
type: backlog_item
tags:
- improvement
- web-ui
- error-handling
kind: improvement
priority: low
effort: XS
status: done
---

## Problem

Sidebar.svelte fires API calls in `onMount` with no error handling, causing silent failures:

- `getAuthConfig()` and `getMe()` promises have no `.catch()` handlers
- If the API is unavailable or returns an error, the sidebar state becomes inconsistent
- User authentication menu may not render or may display stale data
- No logging or user feedback when API calls fail

## Solution

Add error handlers to gracefully degrade when auth endpoints are unavailable:

- Add `.catch()` handlers that log warnings
- Hide user menu or show login prompt when auth check fails
- Set fallback auth state (e.g., `isAuthenticated = false`)
- Consider a retry mechanism for transient failures

## Success Criteria

- All unhandled promises in Sidebar `onMount` have `.catch()` handlers
- Sidebar gracefully degrades if auth API is unavailable
- Warnings logged for debugging
- No silent failures or stale state
