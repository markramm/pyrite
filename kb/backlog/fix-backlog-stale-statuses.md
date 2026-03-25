---
id: fix-backlog-stale-statuses
type: backlog_item
title: "Update 14 stale backlog item statuses and commit untracked notes"
kind: bug
status: proposed
priority: high
effort: S
tags: [kb, backlog, hygiene]
epic: epic-release-readiness-review
---

## Problem

14 backlog items from the Web UI Feature Parity epic are marked done in BACKLOG.md but their frontmatter still says `status: proposed`. Additionally, 14 `kb/notes/web-ui-*.md` files are untracked.

## Items to update

web-ui-editor-theme-mismatch, web-ui-editor-blank-content-bug, web-ui-orient-in-sidebar, web-ui-wikilink-rendering-in-lists, web-ui-user-management, web-ui-index-management, web-ui-daily-notes-calendar, web-ui-entry-metadata-display, web-ui-git-operations, web-ui-entry-creation-fields, web-ui-advanced-search-filters, web-ui-graph-centrality, web-ui-saved-searches, web-ui-kb-orientation-page, quartz-static-site-export

## Fix

Run `pyrite update <id> -k pyrite -f status=done` on each. Move files to `kb/backlog/done/`. Commit untracked note files.
