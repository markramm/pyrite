---
id: add-loading-skeletons-and-improve-loading-states-across-web-app
title: Add loading skeletons and improve loading states across web app
type: backlog_item
tags:
- enhancement
- web
- ux
- polish
importance: 5
kind: feature
status: completed
priority: low
effort: S
rank: 0
---

## Problem

Loading states across the web app are plain 'Loading...' text rather than skeleton UIs that preserve layout during load. No loading indicator visible when navigating or searching on the site cache pages either.

## Solution

Replace text loading states with skeleton/shimmer patterns that match the target layout. Key pages: entries list, search results, timeline, entry detail.

## Scope

Pyrite-general.
