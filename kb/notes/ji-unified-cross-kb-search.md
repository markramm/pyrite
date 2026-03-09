---
id: ji-unified-cross-kb-search
title: Unified cross-KB search with result correlation
type: backlog_item
tags:
- journalism
- investigation
- search
- cross-kb
links:
- target: epic-cross-kb-investigation-search
  relation: subtask_of
  kb: pyrite
kind: feature
status: proposed
priority: high
effort: M
---

## Problem

Pyrite supports multi-KB search via `MultiKBRepository.search()` and the search service, but results are returned as a flat list without correlation. For investigations, the journalist needs to know: "This person appears in 3 KBs — here are the entries from each, and here's how they connect."

## Scope

- Enhanced multi-KB search that groups results by entity identity (not just by KB)
- Entity correlation: match entries across KBs by title, aliases, and ID
- Result format: grouped by entity with per-KB appearances
- MCP tool: `investigation_search_all` — searches all configured KBs + returns grouped results
- CLI: `pyrite investigation search "query" --all-kbs`
- REST API endpoint for the web UI
- Relevance ranking across KBs (not just within each KB)

## Acceptance Criteria

- Single query returns grouped results across all KBs
- Same entity matched across KBs by title/alias similarity
- Results ranked by cross-KB relevance (entity appearing in 3 KBs ranks higher than 1)
- MCP tool returns structured groups usable by Claude Desktop/Cowork
- Performance: <3s for search across 5 KBs totaling 20,000 entries
