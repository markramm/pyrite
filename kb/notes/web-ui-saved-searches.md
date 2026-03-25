---
id: web-ui-saved-searches
title: "Web UI: Saved searches with localStorage persistence"
type: backlog_item
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
kind: feature
status: completed
priority: low
effort: S
---

## Problem

Users who frequently run the same searches must re-type queries and re-apply filters each time. There is no way to bookmark or recall a search configuration within the UI.

## Solution

Allow users to save the current search query and filter state under a user-chosen name, persisted to localStorage. Display saved searches as quick-access pills on the search page. Include edit and delete actions for managing saved searches.
