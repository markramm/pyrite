---
type: backlog_item
title: "Graph Influence-per-Occurrence Metric"
kind: enhancement
status: proposed
priority: low
effort: S
tags: [web, graph, visualization]
---

Surface entries that "punch above their weight" — high influence (betweenness centrality or PageRank) relative to their link count. These are entries with outsized connective importance despite being lightly linked.

- Compute influence ratio: BC (or PageRank) normalized by link count
- Add an "Entrance Points" or "Key Connectors" view that ranks entries by this ratio
- Highlight top influence-per-occurrence entries on the graph with a distinct border or glow
- Useful for identifying entries that deserve more attention or expansion

Inspired by InfraNodus (Paranyushkin, WWW'19) "entrance points" concept — nodes with high influence per occurrence that serve as key access points into the discourse.
