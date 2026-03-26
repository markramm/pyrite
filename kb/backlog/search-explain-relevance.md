---
id: search-explain-relevance
type: backlog_item
title: "Search: Show why an entry matched (relevance explanation)"
kind: feature
status: proposed
priority: medium
effort: M
tags: [search, ux]
epic: epic-cross-kb-discovery
---

## Problem

Search snippets are inconsistent — sometimes they show the relevant passage, sometimes irrelevant parts. For cross-KB discovery, the user needs to see *why* the search engine thinks an entry is relevant. This is especially important for semantic search where the match may be structural (no shared vocabulary).

## Proposed Approach

For keyword search: highlight the matching terms in context (already partially works).

For semantic search: find the paragraph in the entry body whose embedding is most similar to the query embedding, and use that as the snippet. This is "passage retrieval" and would show the user the exact text that drove the similarity score.

Could also add a `--explain` flag that shows the similarity score and matching passage.
