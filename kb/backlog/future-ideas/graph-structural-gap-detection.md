---
type: backlog_item
title: "Graph Structural Gap Detection"
kind: feature
status: proposed
priority: low
effort: L
tags: [web, graph, visualization, ai]
---

Identify clusters of entries that are topically related but not yet linked — "structural gaps" — and surface them as suggested connections or research prompts.

- After community detection, find pairs of clusters with high intra-cluster density but low inter-cluster connectivity
- Highlight gap edges (potential missing links) as dashed lines on the graph
- Show a "Gaps" panel listing cluster pairs with suggested bridge entries
- Optionally use AI to propose *why* two clusters might connect and suggest new entries or links
- Complements the existing "wanted pages" feature by finding missing *relationships*, not just missing *pages*

Inspired by InfraNodus (Paranyushkin, WWW'19) which detects structural gaps between discourse communities to surface blind spots and prompt new insight.
