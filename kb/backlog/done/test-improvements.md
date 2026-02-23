---
type: backlog_item
title: "Shared Test Fixtures and Coverage Gaps"
kind: improvement
status: done
priority: medium
effort: M
tags: [testing, quality, dx]
---

## Summary

The test suite (456 tests) has good coverage of happy paths but significant gaps in error paths, search modes, and CLI commands. Test fixture setup is duplicated across 5 files.

## Issues (from test evaluation)

### Fixture Duplication
KB + config + DB + index setup is copy-pasted in:
- test_rest_api.py, test_mcp_server.py, test_agent_cli.py, test_starred_entries.py, test_integration.py

Fix: Extract shared `pyrite_test_env` fixture into `conftest.py`.

### Coverage Gaps (HIGH priority)
- Endpoint error paths (400/404/500 responses) — barely tested
- Semantic and hybrid search modes — untested
- Query expansion (`expand=True`) — untested
- 24 of 42 CLI functions untested
- MCP tier restrictions (read vs write vs admin) — untested
- Plugin validation conflicts — untested

### Coverage Gaps (MEDIUM priority)
- Config validation edge cases (duplicate KB names, invalid YAML)
- Migration rollback testing
- Concurrent update scenarios
- Template API endpoints (only service tested, not endpoints)

### Test Quality
- Many API tests only check status code, not response body structure
- Integration-heavy: 83% integration tests, 17% unit tests
- Consider `pytest -m integration` marker for slow tests

## Acceptance Criteria

- [x] Shared test fixture in conftest.py (composable: tmp_kb_dir, kb_configs, pyrite_config, pyrite_db, index_mgr, kb_service, sample_events, sample_person, indexed_test_env, rest_api_env)
- [x] Error path tests for all endpoint modules (15 tests: 404, 400, empty results)
- [ ] Semantic and hybrid search modes tested (deferred — requires embedding model setup)
- [x] MCP tier restrictions tested (7 tests: read/write/admin tool exposure)
- [x] 17+ new Typer CLI tests (list, get, timeline, tags, backlinks, create, update, delete, config)
- [x] Pytest markers defined: integration, api, mcp, cli
- Total: 495 tests (456 existing + 39 new)
