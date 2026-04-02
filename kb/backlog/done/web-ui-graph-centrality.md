---
id: web-ui-graph-centrality
title: "Web UI: Wire up graph node sizing by betweenness centrality"
type: backlog_item
tags: [web, ux]
links:
- target: epic-web-ui-feature-parity
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
effort: S
---

## Problem

The graph API returns betweenness centrality per node, and the GraphView component already accepts a `sizeByCentrality` prop. However, the GraphControls checkbox that toggles this prop is never connected to the actual centrality data from the API response, so enabling it has no visible effect.

## Solution

Connect the centrality data from the graph API response to the GraphView component. Map each node's betweenness centrality value to a node radius scale so that toggling the checkbox in GraphControls visually resizes nodes by their structural importance in the knowledge graph.
