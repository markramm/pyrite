---
id: quality-sweep-wall-clock-timeouts-in-tests-fix-450-and-lint-against-importlib
title: 'Quality: sweep wall-clock timeouts in tests, fix #450, and lint against importlib.reload'
type: backlog_item
tags:
- quality
- refactor
- tests
importance: 5
kind: tech_debt
status: proposed
priority: medium
effort: M
rank: 0
---

Retro 12's quality theme, approved by the maintainer 2026-09-26.

- Replace fixed wall-clock waits in tests with barriers and generous deadlines (the pattern in tests/test_task_claim_concurrency.py).
- Fix #450.
- Add a lint or test that forbids importlib.reload and sys.modules eviction in tests. On 2026-09-25 a reload broke isinstance checks in unrelated tests; #510 was the same class.

Done: the pre-push suite passes 3 runs in a row at -n 4 under load with no timing flakes.
