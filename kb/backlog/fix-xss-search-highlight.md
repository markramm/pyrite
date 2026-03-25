---
id: fix-xss-search-highlight
type: backlog_item
title: "Fix XSS: Escape snippet text before highlight markup"
kind: bug
status: proposed
priority: critical
effort: S
tags: [security, xss, frontend]
epic: epic-release-readiness-review
---

## Problem

`web/src/routes/search/+page.svelte:385` — `{@html highlightSnippet(result.snippet, searchStore.query)}` wraps matches in `<mark>` tags but the snippet text itself is not HTML-escaped first. If a snippet contains `<script>`, it passes through raw.

## Fix

HTML-escape the snippet text before applying the regex for `<mark>` tag insertion.
