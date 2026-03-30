---
id: search-domain-aware-expansion
type: backlog_item
title: "Search: Domain-aware query expansion from KB vocabulary"
kind: feature
status: done
priority: medium
effort: L
tags: [search, ai, discovery]
epic: epic-cross-kb-discovery
---

## Problem

The `--expand` flag uses general LLM knowledge to expand queries. But for cross-KB discovery, expansion should come from the KB's own vocabulary. "Seven generations thinking" should expand to "temporal governance", "kaitiakitanga", "long-term thinking", and "Gadaa cycle" — not from general knowledge but from indexed entry content that uses those terms in related contexts.

## Proposed Approach

1. Take the original query
2. Run a quick semantic search to find the top 5 most similar entries
3. Extract key terms/phrases from those entries (TF-IDF or entity extraction)
4. Use those extracted terms as expansion candidates
5. Re-run the search with the expanded query

This is "pseudo-relevance feedback" — a well-known IR technique. The advantage over LLM expansion is that it's grounded in actual KB content, not hallucinated associations.

Alternative: use the LLM but provide the top-5 entry titles/summaries as context for expansion, constraining it to the KB's domain vocabulary.
