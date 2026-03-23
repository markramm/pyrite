---
id: web-ui-daily-notes-calendar
type: backlog_item
title: "Web UI: Calendar widget for daily notes"
kind: feature
status: proposed
priority: medium
effort: S
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

The daily notes page has no visual overview of which dates have existing notes. Users must scroll through a list or guess dates, making it hard to navigate to past notes or spot gaps in their journaling.

## Solution

Add a calendar widget to the daily notes page that highlights dates with existing notes. Clicking a date navigates to that day's note if it exists or offers to create a new note for that date. Use a compact month-view calendar that fits in the page sidebar or header area.
