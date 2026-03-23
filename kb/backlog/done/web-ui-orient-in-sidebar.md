---
id: web-ui-orient-in-sidebar
type: backlog_item
title: "Web UI: Add Orient link to sidebar navigation"
kind: feature
status: proposed
priority: medium
effort: XS
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

The orient page is only reachable by clicking a KB name on the dashboard. There is no persistent navigation link in the sidebar, so users who navigate away cannot easily return to the orient view without going back to the dashboard first.

## Solution

Add an "Orient" link to the sidebar navigation component, placed alongside the other KB-scoped navigation items. Use the existing route and icon conventions.
