---
id: cross-kb-orphan-detection
type: backlog_item
title: "Cross-KB: Detect orphaned high-value concepts"
kind: feature
status: proposed
priority: medium
effort: M
tags: [search, cross-kb, discovery, graph]
epic: epic-cross-kb-discovery
---

## Problem

Some entries are high-importance concepts that should have cross-KB connections but don't. These "orphans" represent gaps in the knowledge graph. Currently there's no way to find them automatically.

## Proposed Interface

```
pyrite links orphans --kb ramm --min-importance 8
```

## Implementation

1. Find entries in the KB with importance >= threshold (or high centrality, many intra-KB links)
2. For each, check how many cross-KB links exist
3. For each, run similarity search across other KBs to estimate how many connections *should* exist
4. Score orphan-ness as: (expected connections based on similarity) - (actual cross-KB links)
5. Return entries ranked by orphan score — high score means "should be connected but isn't"
