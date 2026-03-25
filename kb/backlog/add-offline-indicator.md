---
id: add-offline-indicator
type: backlog_item
title: "Add visual indicator when WebSocket connection is lost"
kind: enhancement
status: proposed
priority: medium
effort: S
tags: [frontend, ux]
epic: epic-release-readiness-review
---

## Problem

The WebSocket client reconnects silently. Users have no way to know they're operating with stale data when the connection drops.

## Fix

Add a subtle banner or status icon in the layout that appears when the WebSocket is disconnected, informing the user that real-time updates are paused.
