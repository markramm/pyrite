---
id: web-graph-default-scope-and-guards
type: backlog_item
title: "Web: graph view — scope to active KB by default, add scale guards, explain centrality in plain language"
kind: improvement
status: proposed
priority: high
effort: M
created: "2026-07-03"
tags: [web, ux, graph, ux-audit-2026-07]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
- target: web-fix-dropped-kb-seams
  relation: related
  kb: pyrite
---

## Problem

The graph view (#2 reported new-user confusion) renders the ENTIRE
multi-KB corpus by default (`routes/graph/+page.svelte:17,31-36` —
`selectedKb=''` → all KBs) with no scale guard: the API supports
`limit` (`api/client.ts:560`) but the page never sends it. On the
production corpus that's thousands of cose-bilkent nodes laid out on
the main thread. Compounding it:

- A "Depth" slider (`GraphControls.svelte:77-88`) that is
  meaningless without a center node — shown anyway.
- Analysis semantics with no explanation: "Size by centrality"
  checkbox, centrality-encoded opacity, tooltips printing raw
  `centrality: 0.043` (`GraphView.svelte:182-190`). Expert
  vocabulary presented cold.
- Dual identity never communicated: it's a navigation tool (tap →
  entry) AND an analysis tool, and nothing says which.
- Hardcoded dark canvas (`#09090b` background, `#a1a1aa` labels —
  `GraphView.svelte:119,271-275`) regardless of theme.
- The legend (the one good discoverability feature,
  `graph/+page.svelte:112-124`) is non-interactive while a separate
  Type dropdown does the filtering.
- Search-highlight dims non-matches with no visible way to clear.

Live-walkthrough confirmation (demo, 2026-07-03, screenshots in the
audit set): the default is a 500-node all-KB hairball on a black
canvas with ~7px truncated grey labels plus a detached grid of
orphan nodes parked top-center; typing "OODA" in "Search nodes…"
produced a PIXEL-IDENTICAL canvas (the node search is a no-op as
shipped); four of the top type colors (writing/concept/note/era) are
near-identical greys so the legend decodes almost nothing; the
graph's own KB dropdown contradicted the sidebar switcher on the
same screen ("guide (27)" vs "boyd"); clicking a node navigates
away and discards all graph state (scope/zoom/layout). The hover
tooltip ("The Military Reform Movement / organization · boyd / 18
links") is genuinely good — build on it.

## Fix

1. Default scope = active KB (per [[web-kb-context-single-authority]]),
   with an explicit "All KBs" escalation showing a node-count
   warning before layout.
2. Always send `limit`; above it, offer "start from a node" (search
   → center → depth) instead of rendering everything.
3. Show the Depth slider only when centered on a node.
4. Plain-language centrality: label the toggle something like
   "Highlight hub entries", one-line explanation in the legend, drop
   raw decimals from tooltips (or move behind a details view).
5. Make the legend interactive (click type → filter) and unify with
   the Type dropdown.
6. Theme-aware canvas colors.
7. State the mode: a small header line ("Click a node to open it")
   makes the navigation affordance explicit before first hover.
8. Fix the node-search no-op (or wire it to highlight+zoom); give
   distinguishable type colors (the dataviz categorical-palette
   problem — 4 greys decode nothing); either lay out orphan nodes
   meaningfully or offer "hide unlinked".
9. Preserve graph state on node click (open entry in a side panel
   or restore scope/zoom on back-navigation).

## Acceptance criteria

- Fresh user on the demo corpus gets a scoped, readable graph in
  <2s, and can navigate to a specific entry via the graph without
  guidance.
- No unbounded whole-corpus layout is reachable without a warning.
