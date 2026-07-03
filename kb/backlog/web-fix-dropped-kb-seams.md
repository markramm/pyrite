---
id: web-fix-dropped-kb-seams
type: backlog_item
title: "Web: fix the three dropped-KB-param seams (orient→graph, graph node tap, orient recent links)"
kind: bug
status: proposed
priority: high
effort: S
created: "2026-07-03"
tags: [web, ux, navigation, ux-audit-2026-07]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
- target: web-kb-context-single-authority
  relation: related
  kb: pyrite
---

## Problem

Three verified small bugs where KB context is dropped on the floor
mid-navigation — quick wins independent of the full
[[web-kb-context-single-authority]] rework:

1. `/orient` renders "View Graph" linking to `/graph?kb={orient.kb}`
   (`routes/orient/+page.svelte:80`) but `routes/graph/+page.svelte`
   never reads `$page.url.searchParams` — the param is silently
   dropped and the graph shows all KBs.
2. Graph node tap navigates `goto('/entries/'+entryId)` discarding
   `data.kbName` that is sitting in the node data
   (`GraphView.svelte:166-169`).
3. Orient's Recent Changes links `/entries/{entry.id}` with no kb
   (`orient/+page.svelte:150`).

## Fix

Small diffs: graph page reads `?kb=` into its `selectedKb`; node tap
and orient links carry the kb param. Do NOT invent a fourth scoping
regime — align with whatever [[web-kb-context-single-authority]]
decides if it lands first; otherwise use `?kb=` consistently.

## Acceptance criteria

- orient→graph handoff scopes the graph to the orient KB.
- Clicking a graph node opens the entry in the correct KB.
