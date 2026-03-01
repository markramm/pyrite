---
id: test-coverage-gaps
title: "Test Coverage Gaps"
type: backlog_item
tags:
- improvement
- testing
- code-hardening
- launch-critical
kind: improvement
priority: high
effort: L
status: planned
links:
- roadmap
- test-infrastructure
---

# Test Coverage Gaps

**Wave 6a of 0.9 Code Hardening.** Fill the biggest untested areas with new test files. 3 parallel agents.

## Items

| Item | New File | Effort | Description |
|------|----------|--------|-------------|
| AI endpoint tests | `tests/test_ai_endpoints.py` | M | Test all 4 AI endpoints (summarize, auto-tag, suggest-links, chat) with mocked LLM service |
| Admin CLI tests | `tests/test_admin_cli.py` | M | Test 25+ admin CLI commands (kb, index, repo, qa, schema, extension) via CliRunner |
| Wikilink service tests | `tests/test_wikilink_service.py` | S | Test all 4 WikilinkService methods (list_entry_titles, resolve_entry, resolve_batch, get_wanted_pages) |

## Definition of Done

- All 3 test files created and passing
- AI endpoints tested with mocked LLM (no real API calls)
- Admin CLI covers happy paths for all command groups
- WikilinkService covers edge cases (missing entries, batch resolution, wanted pages)
- Total test count increases by 40+
