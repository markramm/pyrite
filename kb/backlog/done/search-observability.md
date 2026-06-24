---
id: search-observability
title: "Search observability: log which mode served each query, latency, fallback reason"
type: backlog_item
tags: [search, observability, debugging, logging]
importance: 5
kind: improvement
status: done
priority: medium
effort: S
rank: 0
---

## Problem

`pyrite/services/search_service.py` runs three modes (keyword, semantic,
hybrid + RRF) with several graceful fallbacks (semantic → keyword when
embeddings unavailable, hybrid → keyword if no vectors). None of this is
logged. From outside, you cannot tell:

- Which mode served a particular query
- Why hybrid degraded to keyword for a specific KB
- How long the query took
- Whether the embeddings index is empty for the KB

The result is two open backlog items (`search-fallback-error-obscured`,
`fts-search-result-fragmentation`) that are essentially "we can't see what
search is doing."

This ticket is the small-but-useful first step: make the existing
behavior visible.

## Solution

1. Structured log on every search call:
   ```
   search.query kb=pyrite mode=hybrid actual=keyword reason=no_embeddings
     query_len=23 result_count=12 latency_ms=18
   ```
2. Each search-service method records its decision via a thin
   `SearchTrace` dataclass attached to the response (so the API/MCP
   surface can optionally include it under `--debug`).
3. Counters via the existing logger (no new metrics dep). If
   `prometheus_client` lands later, the counters port cleanly.
4. CLI: `pyrite search --debug` prints the trace alongside results.

## Acceptance criteria

- Every search emits one structured log line.
- `--debug` returns the trace in the response.
- Fallback transitions (semantic → keyword) are visible in the log.
- One smoke test asserting the log line shape.

## Related

- `search-fallback-error-obscured` — adjacent; this one is the prerequisite
- `search-stats-command` — uses similar data, separate scope
- `fts-search-result-fragmentation` — diagnosing this needs the trace
