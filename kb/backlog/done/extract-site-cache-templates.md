---
id: extract-site-cache-templates
title: "Extract site cache HTML/CSS/JS to Jinja2 templates"
type: backlog_item
tags: [architecture, site-cache, maintainability]
kind: enhancement
status: done
priority: high
effort: L
---

## Problem

`site_cache.py` contains 807 lines of inline CSS/HTML/JS as Python format strings. No syntax highlighting, no hot-reload, CSS changes require editing Python source. `static_search_page.py` duplicates 80+ lines of the same CSS.

## Fix

Move templates to `pyrite/server/templates/` as Jinja2 files. Extract shared CSS into a common partial. This enables designer iteration, proper tooling, and eliminates CSS duplication.
