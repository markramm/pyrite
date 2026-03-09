---
id: ji-ui-network-graph
title: Entity network graph visualization
type: backlog_item
tags:
- journalism
- investigation
- web
- frontend
- graph
links:
- target: epic-investigation-ui-views
  relation: subtask_of
  kb: pyrite
kind: feature
status: proposed
priority: high
effort: L
---

## Problem

"Follow the money" investigations center on relationship networks: who owns what, who funds whom, who sits on which boards. A visual network graph lets journalists see the structure, discover indirect connections, and communicate complex relationships.

## Scope

- Force-directed graph component (SvelteKit, likely using D3 or a Svelte graph library)
- Nodes: persons, organizations, assets, accounts (sized by importance, colored by type)
- Edges: ownership, membership, funding, investigation relationships (styled by type, labeled with role/percentage)
- Interactive: drag nodes, zoom, pan, click to select
- Selection: click a node to highlight its connections, show entity summary panel
- Expand/collapse: double-click to expand a node's connections (lazy-load from API)
- Filters: show/hide edge types, filter by importance threshold, time period
- Layout presets: force-directed (default), hierarchical (ownership chains), circular
- Multi-hop paths: highlight shortest path between two selected entities
- Export: PNG/SVG for publication use

## Data Source

- Uses `investigation_network` MCP tool / REST API endpoint
- Configurable depth (1-3 hops from center entity)
- Loads connection entries (ownership, membership, funding) as edges

## Acceptance Criteria

- Graph renders 200+ entity networks without lag
- Ownership chains visible through shell company layers
- Path highlighting between two entities works
- Export produces publication-quality SVG
- Responsive to real-time updates (new connection created via MCP → graph updates)
