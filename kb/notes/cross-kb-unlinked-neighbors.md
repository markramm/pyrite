---
id: cross-kb-unlinked-neighbors
title: "Cross-KB: Find unlinked semantic neighbors for an entry"
type: backlog_item
tags: [search, cross-kb, discovery, graph]
kind: feature
status: done
priority: high
effort: M
---

## Problem

The highest-value discovery workflow is: given entry X, find entries in other KBs that are semantically similar but have no existing link. Currently requires running a search, manually checking cross-kb-links.yaml, and tracking results. Should be one command.

## Proposed Interface

```
pyrite links discover --source ramm/trust-as-operational-mechanism --exclude-linked --limit 10
```

## Implementation

1. Get the embedding for the source entry
2. Run similarity search across all KBs (or specified target KBs)
3. Exclude results from the source entry's own KB (optional flag to include)
4. Exclude results that already have a link (any relation type) to the source
5. Return ranked candidates with similarity score and a relevance snippet

Depends on: embedding service, graph service (for existing link lookup), search service (for similarity).
