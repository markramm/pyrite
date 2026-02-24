---
type: backlog_item
title: "Graph Community Detection and Cluster Coloring"
kind: enhancement
status: proposed
priority: low
effort: M
tags: [web, graph, visualization]
---

Detect topical communities in the knowledge graph and optionally color nodes by detected cluster instead of entry type. Reveals emergent topic groupings that cut across type boundaries.

- Use Cytoscape's Markov clustering or Louvain community detection (via plugin or custom implementation)
- Add a "Color by" toggle in GraphControls: Entry Type vs. Detected Community
- Each community gets a distinct color; legend updates to show community labels (derived from most-central node titles)
- Modularity score shown as a graph-level metric (higher = more distinct clusters)

Inspired by InfraNodus (Paranyushkin, WWW'19) which uses modularity-based community detection to identify topical clusters in text networks.
