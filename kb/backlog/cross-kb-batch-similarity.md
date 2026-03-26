---
id: cross-kb-batch-similarity
type: backlog_item
title: "Cross-KB: Batch similarity search between two KBs"
kind: feature
status: proposed
priority: high
effort: L
tags: [search, cross-kb, discovery]
epic: epic-cross-kb-discovery
---

## Problem

Finding all potential connections between two KBs requires running individual searches for every entry. With 100+ entries per KB, this is impractical. A batch mode that compares all entries in KB-A against KB-B and outputs candidate links would cut work by 80%.

## Proposed Interface

```
pyrite links suggest --source-kb ramm --target-kb senge --min-similarity 0.7 --limit-per-entry 3
```

Output: table of (source_entry, target_entry, similarity_score, snippet) sorted by score.

## Implementation

1. Load all embeddings for source KB
2. For each source entry, run similarity search scoped to target KB
3. Filter by minimum similarity threshold
4. Deduplicate (if A→B and B→A both appear, merge)
5. Exclude already-linked pairs
6. Output as table, JSON, or directly create link entries

Performance note: for large KBs, this could be expensive. Consider caching embeddings in memory and doing batch cosine similarity via numpy rather than N individual DB queries.
