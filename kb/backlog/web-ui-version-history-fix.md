---
id: web-ui-version-history-fix
title: "Fix VersionHistoryPanel — missing API method"
type: backlog_item
tags:
- bug
- frontend
- web-ui
kind: bug
priority: high
effort: XS
status: proposed
links:
- web-ui-review-hardening
---

## Problem

`VersionHistoryPanel.svelte` calls `api.getEntryVersions()` which is not defined in `client.ts`. Opening the version history panel on any entry will throw a runtime error.

## Solution

Either:
1. Add `getEntryVersions(id)` to the API client (if the backend endpoint exists)
2. Or hide/disable the version history panel until the endpoint is ready
