---
id: tests-t8-weak-assertion-sweep-of-the-tests-written-before-360
title: 'Tests T8: weak-assertion sweep of the tests written before #360'
type: backlog_item
tags:
- quality
- test
importance: 5
kind: tech_debt
status: proposed
priority: medium
effort: M
rank: 0
---

Source: test-architecture review 2026-09-25 (theme T8). Milestone 0.27, as the maintainer decided on 2026-09-24.

## Problem

- 28 tests have no assertion at all.
- 41 assert only a type or non-null. Examples: the six `test_services.py::test_search_*` tests assert only `isinstance(results, list)`, and `test_task_dag.py::test_handles_cycle_gracefully` is another.
- 26 REST tests check only a success status on routes that return data or perform a write. `test_endpoint_errors.py:153` asserts `status_code in (200, 201, 404)`.
- 147 regression-named tests have no guard-level red proof from before #360.

## Target shape

Each test asserts the contract its name claims, or it is deleted. A "does not raise" test says so explicitly, with a `# no-raise:` marker and a reason, which the rules test accepts.

## Groom 2026-09-25

**Acceptance** (verbatim from the review):
1. The no-assert and trivial-only detector (rules test) passes, with an allowlist for explicit no-raise tests.
2. The six `test_services.py::test_search_*` type-only tests assert on result content from a seeded corpus.
3. The 26 success-only REST tests assert a response body field or a read-back.
4. `test_endpoint_errors.py:153` asserts one outcome.
5. Sample 20 regression-named tests at random, run the guard-removal check, and report the survival rate. That rate decides whether a second sweep is worth it.

**Touches:** `tests/test_services.py`, `test_backend_conformance.py`, `test_api_tiers.py`, `test_plugin_endpoints.py`, `test_endpoint_errors.py`, `test_truncated_body_refused_on_write.py`, `test_qa_rules.py`, `test_plugin_integration.py`, `test_hook_runner.py`, the other files on the review's scan lists, and `tests/test_test_rules.py` (rule 10).

**Sequence:**
- After T1 (the rules file).
- `test_endpoint_errors.py` is edited by #381. Dispatch after #381 has merged.
- Carve out the auth-adjacent part (`test_api_tiers.py`, `test_truncated_body_refused_on_write.py`, `test_settings_secret_authz.py`) into a second PR after the private security batch. The rest can go first.
- `test_task_dag.py` is edited by T1. T1 goes first.

**Model:** Sonnet. **Size:** M. **Heavy:** yes. **Cold read:** no.

**Out of scope:**
- Re-proving all 147 regression-named tests. Sample 20, and let the rate decide.
- Merging overlapping test files.
- Any product change. A test that turns out to assert a bug gets an issue, not a fix here.
