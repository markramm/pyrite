---
id: web-ui-page-titles
title: "Add document titles to all routes"
type: backlog_item
tags:
- improvement
- frontend
- web-ui
- accessibility
kind: improvement
priority: medium
effort: XS
status: proposed
links:
- web-ui-review-hardening
---

## Problem

Only `/qa` and `/entries/clip` set a `<svelte:head><title>` — all other routes show the default browser tab title. Users with multiple tabs can't distinguish pages.

## Solution

Add `<svelte:head><title>Page Name — Pyrite</title></svelte:head>` to every route. For dynamic pages like entry detail, include the entry title.
