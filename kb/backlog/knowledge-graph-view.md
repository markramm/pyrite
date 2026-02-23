---
type: backlog_item
title: "Interactive Knowledge Graph View"
kind: feature
status: proposed
priority: high
effort: L
tags: [web, graph, phase-3]
---

Full interactive knowledge graph using Cytoscape.js:

**Backend:**
- `GET /api/graph` — returns nodes + edges, supports `center`, `depth`, `type` filter, `limit` params
- New query method in `database.py` for graph data with depth traversal

**Frontend:**
- `GraphView.svelte` — Cytoscape.js with cose-bilkent layout
- `GraphControls.svelte` — filter by type, tag, KB
- `LocalGraph.svelte` — per-entry mini graph (1-2 hops) in entry sidebar
- Color-coded nodes by entry type
- Click node to navigate to entry
- Zoom, pan, drag nodes

npm dependencies: `cytoscape`, `cytoscape-cose-bilkent`

Handles 1k-5k nodes with mobile gesture support.
