---
id: web-ui-loading-states
title: "Standardize loading states across all pages"
type: backlog_item
tags:
- improvement
- frontend
- web-ui
kind: improvement
priority: medium
effort: S
status: proposed
links:
- web-ui-review-hardening
---

## Problem

Loading indicators are inconsistent:
- Some pages show "Loading..." text
- Collections list uses a CSS spinner
- Some pages show nothing during load

## Solution

Pick one pattern (spinner + text) and apply it consistently. Consider a shared `LoadingState` component to match the existing `EmptyState` and `ErrorState` components.
