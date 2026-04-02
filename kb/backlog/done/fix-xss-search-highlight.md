---
id: fix-xss-search-highlight
title: "Fix XSS: Escape snippet text before highlight markup"
type: backlog_item
tags: [security, xss, frontend]
kind: bug
status: done
priority: critical
effort: S
---

## Problem

`web/src/routes/search/+page.svelte:385` — `{@html highlightSnippet(result.snippet, searchStore.query)}` wraps matches in `<mark>` tags but the snippet text itself is not HTML-escaped first. If a snippet contains `<script>`, it passes through raw.

## Fix

HTML-escape the snippet text before applying the regex for `<mark>` tag insertion.
