---
id: search-include-body-optional-body-truncation-with-body-truncated-flag-r2000-follow-up
title: 'Search --include-body: optional body truncation with body_truncated flag (r2000 follow-up)'
type: backlog_item
tags:
- search
- cli
- enhancement
importance: 5
status: proposed
priority: medium
rank: 0
---

Follow-up from r2000 (search-include-body-empty), which closed the primary bug (body field is populated when --include-body is set; verified at HEAD and locked by tests test_search_include_body_populates_body_field / test_search_without_include_body_omits_body_field in test_cli_json_output.py).

Ticket criterion (2) remains open: 'Large bodies are truncated with metadata indicating truncation'. Currently the body field is returned in full when --include-body is set. For very large entries (50KB+ bodies), a search returning 20 results with full bodies = 1MB+ of JSON, which slows agent-driven workflows and blows token budgets.

Proposal:
  1. Add --body-max-bytes <N> flag (default: unlimited for backward compat).
  2. When set, truncate each result's body to N bytes and add 'body_truncated': true alongside 'body_truncated_at': <byte offset>.
  3. Keep snippet field intact for the truncated case.
  4. Mirror the same flag in REST /search endpoint and kb_search MCP tool.

Acceptance:
  - --include-body --body-max-bytes 1000 returns truncated bodies with the truncation flag.
  - Default behavior (no --body-max-bytes) is unchanged — backward compatible.
  - Test added to lock both paths.

Effort: S. Defer until a real workflow surfaces 1MB+ response complaints — at that point the truncation default may also need to change to e.g. 10KB for safety.
