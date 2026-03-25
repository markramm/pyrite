---
id: web-ui-entry-metadata-display
title: "Web UI: Entry metadata display on detail pages"
type: backlog_item
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
kind: feature
status: completed
priority: high
effort: M
---

## Problem

Entry detail pages do not render most metadata fields. The API returns importance, status, date, sources, participants, and custom metadata, but the web UI only shows the title, body, type, and tags. Users cannot see structural metadata without using the CLI or reading raw files.

## Solution

Add metadata display components to the entry detail page: an importance badge (1-10), a colored status pill, formatted date, a sources list with links, a participants list, and a key-value table for custom metadata fields. Conditionally render each section only when the field is present.
