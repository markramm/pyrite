---
id: web-ui-review-system
type: backlog_item
title: "Web UI: Surface QA review system"
kind: feature
status: proposed
priority: medium
effort: M
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

The QA review system is fully implemented on the backend with a complete `/api/reviews` endpoint, but the web UI has no page or component that surfaces it. Users cannot create reviews, view review history, or see coverage metrics without using the API or CLI directly.

## Solution

Create a reviews section in the web UI with the ability to create a new review (selecting scope and parameters), view review history as a sortable list, inspect individual review results with issue details, and display coverage metrics showing what percentage of entries have been reviewed. Link review results back to the relevant entries.
