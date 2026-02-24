---
type: backlog_item
title: "Dataview-Style Embedded Queries"
kind: feature
status: retired
priority: medium
effort: XL
tags: [web, editor, query]
---

Embedded queries in entries that dynamically list/filter/sort other entries:

**Syntax (in fenced code blocks):**
```
\`\`\`query
type: event
date > 2024-01-01
tags includes investigation
sort: date desc
limit: 20
\`\`\`
```

**Renders as:** a live table/list of matching entries, updated on view.

**Implementation:**
- Query parser (simple DSL or JSON)
- CodeMirror decoration renders query results inline
- Backend endpoint for executing structured queries
- Caching layer to avoid re-querying on every render

Obsidian's Dataview is its most popular community plugin (~10M downloads). Transforms static notes into a dynamic research database. Particularly valuable for journalists tracking events, sources, and timelines.

**Depends on:** Phase 2 editor infrastructure
