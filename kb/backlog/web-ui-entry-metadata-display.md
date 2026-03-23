---
id: web-ui-entry-metadata-display
type: backlog_item
title: "Web UI: Entry metadata display on detail pages"
kind: feature
status: proposed
priority: high
effort: M
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

Entry detail pages do not render most metadata fields. The API returns importance, status, date, sources, participants, and custom metadata, but the web UI only shows the title, body, type, and tags. Users cannot see structural metadata without using the CLI or reading raw files.

## Solution

Add metadata display components to the entry detail page: an importance badge (1-10), a colored status pill, formatted date, a sources list with links, a participants list, and a key-value table for custom metadata fields. Conditionally render each section only when the field is present.
