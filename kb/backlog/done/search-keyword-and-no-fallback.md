---
id: search-keyword-and-no-fallback
title: "Keyword FTS search is implicit-AND with no relaxation or semantic fallback"
type: backlog_item
tags: [search, fts, recall, ux]
importance: 5
kind: bug
status: done
priority: high
effort: M
rank: 0
---

## Problem

Default keyword search has brittle recall: long natural-language queries return 0 results
even when a matching entry exists, because a single absent term zeroes the result set.

Demonstrated on a live run:
- `"Orange County Florida IGSA ICE terminate"` → 1 hit
- `"...terminate immediately quarterly"` → 0 hits

Root cause chain:
- Default `search_mode = "keyword"` — `pyrite/config.py:336`
- `entry_fts MATCH ?` is column-less → implicit AND across every stemmed term; every
  term must appear — `pyrite/storage/backends/sqlite_backend.py:167`
- There is NO keyword→semantic fallback, no OR-relaxation, no retry on 0 results —
  `pyrite/services/search_service.py` has no fallback path.

Semantic mode (`-m semantic/hybrid`) works but is currently weak:
- `all-MiniLM-L6-v2` (384-dim) with bodies clipped to 500 chars before embedding —
  `pyrite/services/embedding_service.py:34,43`
- `max_distance = 1.3` cutoff — `pyrite/services/search_service.py:209`

## Fix

On 0 keyword hits, relax to OR-combined terms or fall back to semantic search. Consider
hybrid-by-default. Raise or remove the 500-char embedding clip for the MiniLM models.
Pairs well with `[[search-observability]]` (log which mode served the query and why a
fallback fired).

Distinct from `[[epstein-like-search-boolean-and]]` (that one wants *more* AND on the
Epstein LIKE path; this wants AND-*relaxation* + fallback on the main FTS path) and from
`[[fts-search-result-fragmentation]]` (document fragmentation, not recall).

## Provenance

Diagnosed 2026-06-23 from a live daily-capture run. Filed from the daily-capture skill's
PYRITE-FEATURE-REQUESTS.md (Search Bug S2).

## Workaround

For dedup checks, prefer deterministic `grep -li "<key fact>"` over filenames/bodies
rather than relying on `kb search` recall; keep queries to 2-3 high-salience terms.
