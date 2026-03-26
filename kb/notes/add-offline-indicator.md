---
id: add-offline-indicator
title: "Add visual indicator when WebSocket connection is lost"
type: backlog_item
tags: [frontend, ux]
kind: enhancement
status: done
effort: S
---

## Problem

The WebSocket client reconnects silently. Users have no way to know they're operating with stale data when the connection drops.

## Fix

Add a subtle banner or status icon in the layout that appears when the WebSocket is disconnected, informing the user that real-time updates are paused.
