---
id: search-query-syntax-error-contract
type: backlog_item
title: "Search: sanitizer bypass crash → QUERY_SYNTAX error code; document the auto-quote rule on every surface"
kind: bug
status: proposed
priority: high
effort: S
created: "2026-07-02"
tags: [search, fts, errors, mcp, agent-dx, field-reported]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
---

## Problem

Three coupled defects, all reproduced live 2026-07-02, same family as
the fixed `links orphans` crash (40e7a39):

1. **Sanitizer bypass**: `search_service.py:69-97` auto-quotes
   special-char tokens BUT skips sanitization entirely when the query
   contains ` AND `, ` OR `, ` NOT `, or any `"`. So
   `pyrite search '"family separation" cross-link'` crashes with raw
   `sqlite3.OperationalError: no such column: link` — the quote
   disabled sanitization and FTS5 parsed `cross-link` as a column
   filter. Mixed literal+operator queries are exactly what agents
   write.
2. **Error miscoding, MCP**: that OperationalError falls through to
   `_dispatch_tool`'s catch-all → `_error("INTERNAL", str(e),
   retryable=True)`. Agents get "internal, retryable" for a
   deterministic syntax error → pointless retry loops. There is no
   QUERY_SYNTAX code.
3. **Error off-contract, CLI**: `search_commands.py:238` emits
   `{query, count: 0, results: [], error, error_type}` —
   `error_type` (Python class name) instead of the canonical
   `error_code`, no `retryable` (contract: `pyrite/utils/errors.py`).
   The highest-traffic command violates the June error-shape sweep
   exactly when it breaks.

## Fix

- Catch OperationalError (and the Postgres tsquery equivalent) in the
  search path; classify as `QUERY_SYNTAX`, `retryable: false`,
  suggestion: "quote tokens containing - : . yourself when your query
  uses AND/OR/NOT or phrase quotes". Same code on CLI (canonical
  shape via `cli_error`) and MCP (`_error("QUERY_SYNTAX", ...)`).
- Either extend the sanitizer to quote bare special-char tokens even
  in operator queries (parse-aware), or keep the bypass and document
  it — but the error must be classified either way.
- Document the auto-quote/bypass rule in one sentence on BOTH
  surfaces: `search --help` and the `kb_search` MCP description
  (tool_schemas.py:14, currently just "Supports FTS5 query syntax").
- While in there: note on `--status`/`status` param (both surfaces)
  that it filters the indexed `status` frontmatter field — other
  metadata fields (e.g. `readiness`) are not reachable via this flag.
  This known gotcha currently lives only in the operator's memory
  notes and external skills.

## Acceptance criteria

- `pyrite search '"family separation" cross-link' -k <kb>` returns
  results or QUERY_SYNTAX — never a raw OperationalError.
- MCP: same query → `{error_code: "QUERY_SYNTAX", retryable: false,
  suggestion: ...}`.
- Regression tests for: hyphen bare term, hyphen term + phrase quote,
  hyphen term + NOT operator, colon term, on both backends.
- `search --help` exclusion example corrected (see
  [[docs-onboarding-fiction-sweep]] item 5) and the bypass rule
  documented in help + MCP schema.
