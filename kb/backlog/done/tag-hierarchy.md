---
type: backlog_item
title: "Tag Hierarchy and Nested Tags"
kind: feature
status: done
priority: high
effort: M
tags: [web, organization, search]
---

Support hierarchical tags using `/` separator:

- `#project/pyrite/backend`, `#project/pyrite/frontend`, `#source/interview`
- Tag tree view in sidebar (collapsible hierarchy)
- Filtering by parent tag includes all children
- Autocomplete suggests existing tag paths
- Backend: store flat but query with prefix matching (`tag LIKE 'project/pyrite/%'`)
- Migration: existing flat tags continue to work

Obsidian power feature. Flat tags don't scale for research KBs with hundreds of tags — journalists tagging sources, topics, and projects need hierarchy.
