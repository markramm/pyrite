---
id: epic-cross-kb-discovery
type: backlog_item
title: "Epic: Cross-KB Discovery and Link Suggestion"
kind: epic
status: in_progress
priority: high
effort: XL
tags: [epic, search, graph, cross-kb, discovery]
---

## Problem

When working across multiple KBs (e.g., 27 lean/agile/systems thinking KBs), discovering meaningful connections is manual and tedious. The current workflow requires: (1) broad semantic search, (2) manually noting which KBs appear, (3) checking whether connections already exist in cross-kb-links, (4) tracking new vs. known discoveries. A tool that showed "similar AND unlinked" would eliminate most of that overhead.

**What works well today:**
- Semantic search finds connections keyword search cannot (structural parallels across different vocabularies)
- Hybrid mode returns the most useful mixed results for targeted queries
- FTS5 keyword search is fast and precise for known terms
- KB-scoping flag (`--kb`) is useful for targeted follow-up

**What doesn't work:**
- No way to search for cross-KB pairs directly
- Result ranking dominated by largest KBs (no per-KB grouping)
- No negative filtering for already-linked entries
- No batch query capability (16 individual searches instead of 1)
- Snippet quality inconsistent — doesn't show *why* an entry matched

## Items

### Core Discovery Commands

- `cross-kb-unlinked-neighbors` — `pyrite links discover --source <entry> --exclude-linked --limit N`. Find top N semantically similar entries across all KBs, excluding already-linked ones. The single most useful command for the workflow.

- `cross-kb-batch-similarity` — `pyrite links suggest --source-kb <A> --target-kb <B> --min-similarity 0.7`. For every entry in A, find the most similar entry in B above threshold. Output candidate cross-KB links. Replaces many manual searches.

- `cross-kb-orphan-detection` — `pyrite links orphans --kb <name> --min-importance N`. Find high-importance entries with few or no cross-KB links relative to their semantic similarity to entries in other KBs.

- `cross-kb-asymmetric-links` — `pyrite links asymmetric --kb-a <A> --kb-b <B>`. Find entries where A links to B but B doesn't link back, or where similarity suggests a bidirectional link.

### Search Improvements

- `search-group-by-kb` — `--group-by-kb --limit-per-kb N` result mode. Returns top N results from each KB instead of top N globally. Prevents large-KB dominance and reveals cross-domain spread.

- `search-domain-aware-expansion` — Query expansion from the KB's own vocabulary rather than general LLM knowledge. "Seven generations" should expand to "temporal governance", "kaitiakitanga", "long-term thinking" based on indexed content.

### UX

- `search-explain-relevance` — Show why an entry matched (which passage drove the similarity score), not just a generic snippet.

## Discovery Workflow Vision

```
# Stage 1: Find unlinked neighbors for a concept
pyrite links discover --source ramm/trust-as-operational-mechanism --exclude-linked --limit 10

# Stage 2: Batch-find all cross-KB candidates between two KBs
pyrite links suggest --source-kb ramm --target-kb senge --min-similarity 0.7

# Stage 3: Find orphaned high-value concepts
pyrite links orphans --kb ramm --min-importance 8

# Stage 4: Review and formalize
pyrite links create --from ramm/trust --to senge/learning-org --relation structural_parallel
```

## Completed

- `cross-kb-unlinked-neighbors` — **done** (CLI + MCP tool, keyword/semantic/hybrid)
- `search-group-by-kb` — **done** (API query param, round-robin interleaving)

## Future (merged from epic-cross-kb-investigation-search)

- Entity deduplication across KBs (same person/org appearing in multiple investigations)
- "Known entities" reference KB pattern
- External MCP source correlation (search external data sources alongside local KBs)
