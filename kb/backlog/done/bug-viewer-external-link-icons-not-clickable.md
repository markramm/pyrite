---
id: bug-viewer-external-link-icons-not-clickable
title: 'Bug: Viewer external link icons not clickable'
type: backlog_item
tags:
- bug
- viewer
- cascade
importance: 5
kind: bug
status: completed
priority: medium
effort: XS
rank: 0
---

## Problem

The square-arrow icons on the right side of each row in the Timeline Explorer viewer appear clickable but don't respond to clicks. They don't open in a new tab or navigate anywhere.

## Fix

The icons need click handlers that navigate to the entry detail page (or open in new tab).

## Scope

Cascade viewer component (may be Pyrite-general if the viewer is reusable).
