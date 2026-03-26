---
id: search-group-by-kb
title: "Search: Group results by KB with per-KB limit"
type: backlog_item
tags: [search, ux]
kind: feature
status: done
priority: high
effort: S
---

## Problem

When searching across 27 KBs, results are dominated by the largest KBs. A search for "trust as coordination mechanism" returns 4 ramm entries and 3 schneier entries, pushing less-obvious matches in weinberg, senge, and tps off the results entirely. What the user wants is the *best match from each KB* to see the cross-domain spread.

## Proposed Interface

```
pyrite search "decentralized coordination" --mode semantic --group-by-kb --limit-per-kb 2
```

## Implementation

1. Run the normal search with a higher internal limit (e.g., limit * num_kbs)
2. Group results by kb_name
3. Take top N per KB
4. Re-sort groups by best score within each
5. Return interleaved results

This is a presentation-layer change — the search backend doesn't need to change. Could also be exposed as `groupBy=kb&limitPerGroup=2` in the API.
