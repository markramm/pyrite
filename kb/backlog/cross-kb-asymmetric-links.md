---
id: cross-kb-asymmetric-links
type: backlog_item
title: "Cross-KB: Detect asymmetric links between KBs"
kind: feature
status: proposed
priority: low
effort: M
tags: [graph, cross-kb, discovery]
epic: epic-cross-kb-discovery
---

## Problem

When KB-A links to KB-B but KB-B doesn't link back, the connection is one-directional. If semantic similarity suggests the link should exist in both directions, the missing reverse link represents a gap.

## Proposed Interface

```
pyrite links asymmetric --kb-a ramm --kb-b consensus-democracy
```

## Implementation

1. Find all cross-KB links from A→B
2. Find all cross-KB links from B→A
3. Identify pairs where only one direction exists
4. For each asymmetric pair, check semantic similarity to estimate whether the reverse link is warranted
5. Output candidates for reverse linking
