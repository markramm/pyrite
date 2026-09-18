---
id: tests-leak-open-pyritedb-connections-into-temporarydirectory-teardown
title: Tests leak open PyriteDB connections into TemporaryDirectory teardown
type: backlog_item
tags:
- testing
- tech-debt
- quality
importance: 5
kind: tech_debt
status: proposed
priority: medium
effort: S
rank: 0
---

## Problem

Nine test files open a `PyriteDB` inside a `tempfile.TemporaryDirectory()` and
never close it (`test_auth_service.py` ×3, `test_auth_service_oauth.py`,
`test_api_wikilinks.py`, `test_api_security.py`, `test_export_to_repo.py`,
`test_llm_usage_service.py`, `test_kb_permissions.py`, `test_repo_endpoints.py`;
`test_api_tiers.py` was the same and is fixed). An open SQLite connection in WAL
mode can recreate `-wal`/`-shm` files while the directory is being deleted, and
teardown fails with `OSError: Directory not empty`. Seen twice under `-n auto`
in `test_api_tiers` before its fix; the others are the same race waiting for
load.

## Fix

Either close in the fixture (`try: yield ... finally: db.close()`, as in
`test_api_tiers.py`), or better, one shared fixture in `tests/conftest.py`
(`make_client(tmp_path, **settings)`) that owns the DB and closes it, replacing
the five hand-rolled `_make_client` helpers. Consider a `PyriteDB.__enter__/
__exit__` so `with PyriteDB(path) as db:` is the idiom.

## Acceptance

- [ ] `grep -c "PyriteDB(" tests/*.py` sites all have a matching close or use
      the shared fixture.
- [ ] 10 consecutive `pytest -n auto` runs with no teardown errors.

Found during the 2026-09-17 test-suite profiling (0.24.2).
