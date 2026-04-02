---
id: web-ui-advanced-search-filters
title: "Web UI: Advanced search filters (date, tags, fields, expansion)"
type: backlog_item
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
priority: high
effort: M
---

## Problem

The search page only exposes a text query input. The backend supports date range filtering, tag filtering, field projection, and query expansion, but none of these are accessible from the web UI. Power users must construct API calls manually to use advanced search features.

## Solution

Add a collapsible advanced filters panel to the search page with a date range picker (from/to), a tag multi-select filter with autocomplete, field projection checkboxes to control which fields appear in results, and a query expansion toggle. Serialize filter state into query parameters so searches are shareable via URL.
