---
id: task-status-children-tree-view
type: backlog_item
title: "Add child-task tree view to `pyrite task status` for epic-level grooming"
kind: feature
status: proposed
priority: low
effort: S
tags: [task-system, cli, conductor-workflow, grooming, epic-tracking, ux]
---

## Problem

When the conductor grooms an epic with many children (Mark-theme parent-epics this session had 8–13 children each), there's no fast way to see "what's the current state distribution of this epic's children" without:

1. `pyrite task list --format json | python3 -c "filter by parent"` — works but verbose
2. Manual inspection of each child task individually

The conductor needs a one-shot epic-tree view to make grooming decisions like "this epic's children are 6 done + 2 in_progress + 4 open; the in_progress ones are stale; sweep them and reprioritize the open ones."

## Proposed solution

Extend `pyrite task status <id>` with a `--children` (or `--tree`) flag:

```
pyrite task status epic-kleptocratic-authoritarian-takeover-resistance-comparative -k cascade-research --children

epic-kleptocratic-authoritarian-takeover-resistance-comparative (P9, open)
├── case-study-poland-tusk-defeats-pis-2023 (P7, done)
├── case-study-brazil-lula-defeats-bolsonaro-2022 (P7, done)
├── case-study-turkey-erdogan-holds-2023 (P7, done)
├── case-study-india-modi-bjp-loses-majority-2024 (P7, done)
├── case-study-south-korea-yoon-martial-law-impeachment (P7, done)
├── case-study-venezuela-maduro-holds-2024 (P7, done)
├── case-study-belarus-lukashenko-holds-2020-2024 (P7, done)
├── network-map-vance-to-orban-hungary-axis (P7, done)
├── network-map-cnp-to-international-right (P7, done)
├── network-map-federalist-society-to-international-judicial-illiberalism (P7, open)
├── network-map-thiel-network-to-international-authoritarian-aligned (P7, open)
├── synthesis-theme-comparative-resistance-what-worked-what-didnt (P7, open)
└── synthesis-theme-us-players-as-network-node-in-international-illiberal-coalition (P7, open)

Summary: 13 children · 9 done (69%) · 0 in_progress · 4 open · 0 blocked
```

Plus optional `--depth N` for multi-level (grandchildren). Default depth 1.

Status summary line at end is the load-bearing piece — it tells the conductor whether this epic is at a tipping point for promotion / closure / continued dispatch.

## Related

- The `parent` field already exists in task frontmatter (per `pyrite task create --parent` flag); this is purely a query-display feature
- Pairs naturally with bulk-update by parent: `pyrite task bulk-update --filter "parent:<epic-id> AND status:in_progress AND age>2h"`

## Effort

S — query (already supported) + tree rendering + summary calculation. No schema changes.
