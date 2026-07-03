---
id: backend-agnostic-query-dsl
type: backlog_item
title: "Backend-agnostic query DSL: parse → AST → compile per backend"
tags: [search, dsl, backend, architecture, agents]
kind: feature
status: proposed
priority: medium
effort: L
---

> Re-prioritized high → medium 2026-07-02: preparatory architecture with
> no second consumer forcing it yet — SQLite FTS5 leakage is a real
> wart, but nothing operational is blocked on it. Revisit when a
> Postgres-first deployment (or the shared-instance pilot's web search)
> hits the syntax mismatch in practice.

## Problem

Search today leaks the backend's query language to the caller. A query string is
interpreted as **raw SQLite FTS5 syntax**: hyphens become NOT, colons become column
filters, dots become column prefixes. So an agent (or human) must know FTS5 to write a
non-trivial query — and one wrong special char throws a raw `sqlite3.OperationalError`
(`pyrite/storage/backends/sqlite_backend.py:167`, `MATCH ?`).

The current mitigation, `SearchService.sanitize_fts_query()`
(`pyrite/services/search_service.py:68`), is a single regex chokepoint that quotes
special-char tokens and otherwise passes operator-containing queries through untouched
(line 90). It's a patch over FTS5, not an abstraction above it. Postgres uses an entirely
different syntax (`tsquery`, `postgres_backend.py`), so the same query string is not
portable across backends.

Three concrete consequences, all observed in a live daily-capture run (2026-06-23):

- **Agents can't write reliable queries** without backend knowledge — the core ask.
- **Common metadata filters aren't first-class.** Filtering by `status` is routine but
  has no in-query form and (separately) no CLI flag — see `[[search-status-filter-cli]]`.
- **Brittle recall** — implicit-AND with no relaxation or fallback,
  see `[[search-keyword-and-no-fallback]]`.

## Decision direction

Introduce a small **neutral query DSL** that callers learn once, parse it to a
backend-independent **AST**, and **compile the AST per backend** (FTS5 now; Postgres
`tsquery` and an embedded engine later). See ADR-0028.

Proposed surface syntax (one language for agents and humans):

- Boolean + grouping: `ICE AND (detention OR deportation)`, `-exclude`, `"exact phrase"`
- Fielded filters in-query: `status:unprocessed`, `tag:surveillance`, `type:event`,
  `actor:"Jane Doe"`, `date:>2026-01-01`
- These fielded terms compile to the **structured filter params** that already exist on
  `BaseBackend.search()` (kb/type/date/tags/lifecycle/fips/state — ADR-0026 pattern),
  NOT to FTS column syntax. Full-text terms compile to the backend's text-match dialect.

Fold in two robustness wins the AST makes cheap:

- **0-result fallback**: on empty keyword hits, relax AND→OR or fall back to semantic
  (subsumes `[[search-keyword-and-no-fallback]]`).
- Surface clean syntax errors instead of raw backend exceptions.

## Phasing

1. **Phase 1 — DSL + FTS5 compiler + fielded filters + 0-result fallback** (this item's
   core). Slots into the `sanitize_fts_query` chokepoint and the `BaseBackend.search`
   seam. Compile fielded terms to existing structured params. ~3-5 days.
2. **Phase 2 — Relevance behind the seam.** FTS5 BM25 per-column weighting (title > body)
   — achievable without a new engine. Benchmark before escalating.
3. **Phase 3 — Embedded engine backend (Tantivy) if relevance/typo-tolerance demand it.**
   `TantivyBackend(BaseBackend)` + AST→Tantivy compiler. DSL means zero caller changes —
   flip a backend flag. Meilisearch/Typesense become an additional server-side backend
   once the multiuser server is primary (see `[[project_v1_multiuser]]` direction).

## Why now

No major users are on Postgres yet, so the `BaseBackend` search seam can change without a
migration. This is the cheap moment to lock the query-language/backend contract. The clean
`BaseBackend` ABC + `capabilities.py` dispatch map already provide the seam an engine plugs
into.

## Relationship to other items

- Subsumes `[[search-keyword-and-no-fallback]]` (the fallback lands here).
- Provides the in-query form of `[[search-status-filter-cli]]` (`status:` term); the
  plain `--status` flag can still ship independently and sooner.
- Independent of `[[search-stale-index-silent]]` (index freshness, separate fix).
- Distinct from `[[epstein-like-search-boolean-and]]` and
  `[[fts-search-result-fragmentation]]` (Epstein LIKE/fragmentation, not the main FTS DSL).

## Provenance

Designed 2026-06-23 from a daily-capture search review. Decision recorded in ADR-0028.
