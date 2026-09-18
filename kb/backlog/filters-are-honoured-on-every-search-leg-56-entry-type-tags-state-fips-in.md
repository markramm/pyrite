---
id: filters-are-honoured-on-every-search-leg-56-entry-type-tags-state-fips-in
title: 'Filters are honoured on every search leg (#56): entry_type, tags, state, fips in semantic and hybrid'
type: backlog_item
tags:
- search
- mcp
- cli
- rest
- milestone-0.24.2
kind: bug
status: in_progress
priority: high
assignee: agent:pyrite-worker
effort: M
---

## Theme: filters are honoured on every search leg (#56)

Closes #56 (milestone 0.24.2; also closes the CLI-side duplicate #53). `heavy: no`. Model: opus. Cold read: yes (storage protocol + a public search shape).

### Why

`kb_search` defaults to `mode: "hybrid"`. In hybrid and semantic modes `entry_type`, `tags`, `state` and `fips` are silently ignored: the filters are compiled into the FTS/SQL leg's `WHERE`, the vector leg is queried unfiltered (`_semantic_search` ~:336, `_hybrid_search` ~:361 call the backend with `kb_name` only), and the results are fused; only `status` is post-filtered (~:410). A researcher asking for mechanisms gets themes; the default path lies. Reproduced from the MCP tools and the CLI (`--type` ignored, #53) on 2026-09-18.

### Acceptance (from the ticket, verbatim where it matters)

1. Pick option 1 or 2 explicitly and say which in the report — **never 3 alone**:
   - (1) apply the filters on the vector leg: `SearchBackend.search_semantic` (`pyrite/storage/backends/protocol.py:128`) and all four implementations (`sqlite_backend.py:314`, `postgres_backend.py:320`, `overlay_backend.py:327`, plus any in-memory/test backend) take the same filter set the keyword leg takes; the 66 conformance tests in `tests/backends/test_backend_conformance.py` gain the semantic-filter cases;
   - (2) failing that, post-filter the fused set in `SearchService`, with the `limit` honoured *after* filtering (over-fetch and refill so a filtered hybrid query still returns up to `limit` rows), and a note in the report on what that costs at high `limit`.
   Either way, when a filter cannot be honoured by a leg, the response carries `warnings: [...]` naming it — never silently dropped.
2. A test per filter × mode — `entry_type`, `tags`, `state`, `fips`, `status` × `keyword`, `semantic`, `hybrid` — with a bogus value returning 0 results and a valid value returning only matching entries, on both backends (SQLite and Postgres via the conformance harness; skip Postgres cleanly if unavailable, as the suite already does). New file `tests/test_search_filters_across_modes.py`.
3. REST `GET /api/search` (`pyrite/server/endpoints/search.py`) and the CLI `pyrite search --type/--tags/…` reach the same service and are covered by at least one test each through their own entry point.
4. Record, in the report, what a search response owes its caller (the `filters_dropped`/`warnings` shape you chose) — #54 will be settled against that sentence; do not implement #54.
5. CHANGELOG line; close #53 by reference in the PR body (`Closes #53`).

### Touches

Existing: `pyrite/services/search_service.py`, `pyrite/storage/backends/protocol.py`, `sqlite_backend.py`, `postgres_backend.py`, `overlay_backend.py`, `pyrite/server/endpoints/search.py`, `tests/backends/test_backend_conformance.py`, `pyrite/server/tool_schemas.py` only if a `warnings` field is documented, `CHANGELOG.md`. New: `tests/test_search_filters_across_modes.py`.
Out of scope: #59 (entry_type vocabulary drift — a decision, not this theme); #62 (`kb_timeline` `kb_name`); the "unknown entry_type is a VALIDATION error" idea (new public error contract — note it, do not do it); any change to ranking/fusion weights.
