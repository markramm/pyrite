---
id: extract-site-cache-templates
type: backlog_item
title: "Extract site cache HTML/CSS/JS to Jinja2 templates"
kind: enhancement
status: proposed
priority: high
effort: L
tags: [architecture, site-cache, maintainability]
epic: epic-release-readiness-review
---

## Problem

`site_cache.py` contains 807 lines of inline CSS/HTML/JS as Python format strings. No syntax highlighting, no hot-reload, CSS changes require editing Python source. `static_search_page.py` duplicates 80+ lines of the same CSS.

## Fix

Move templates to `pyrite/server/templates/` as Jinja2 files. Extract shared CSS into a common partial. This enables designer iteration, proper tooling, and eliminates CSS duplication.
