---
id: web-ui-collection-editing
type: backlog_item
title: "Web UI: Collection CRUD and query builder"
kind: feature
status: proposed
priority: low
effort: M
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
---

## Problem

Collections cannot be created, edited, or deleted from the web UI. Virtual collections require writing query definitions by hand, and there is no way to configure collection view settings (layout, sorting, grouping) through the browser.

## Solution

Add collection management pages with create, edit, and delete operations. Include a visual query builder for virtual collections that lets users compose filter criteria without writing raw queries. Add view configuration controls for choosing layout mode (list, grid, board), sort field and direction, and grouping field. Persist view configuration per collection.
