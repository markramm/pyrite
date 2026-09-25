---
id: tests-t2b-one-shared-auth-world-for-the-read-only-scoping-matrices
title: 'Tests T2b: one shared auth world for the read-only scoping matrices'
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

Source: test-architecture review 2026-09-25 (theme T2, part b). Milestone 0.27, as the maintainer decided on 2026-09-24. Part a (bcrypt cost 4 in tests) is its own 0.26 item. The two halves are one theme, split into two PRs only because this half has to wait for the private security batch, which is adding tests to exactly these files.

## Problem

The `env` fixtures in the scoping files are function-scoped, although most matrix tests only read. Each builds an app and registers two users per test. After part a the hashing is cheap, but the per-test app and world are still rebuilt 433 times in `test_private_kb_read_scoping.py`.

## Target shape

The read-only matrix classes in the scoping files share a class- or module-scoped world. Tests that mutate grants keep a function-scoped one.

## Groom 2026-09-25

**Acceptance** (verbatim from the review's T2 criteria that apply to part b):
1. `test_private_kb_read_scoping.py` serial wall time falls by at least 60% (report before and after on the same machine, same load). Measure against the post-part-a baseline, and report both numbers.
2. No test in the scoping files changes assertions. Only fixture scope moves.

**Touches:**
- Existing: `tests/test_private_kb_read_scoping.py`, `tests/test_mcp_read_scoping.py`, `tests/test_mcp_write_scoping.py`, `tests/test_auth_endpoints.py`.
- If T4 has landed, the shared worlds should come from its builder.

**Sequence:**
- After the private security batch has landed. It adds tests to these four files.
- After T2a (0.26).
- Preferably after T4, so the shared worlds use the builder.

**Model:** Sonnet. **Size:** M. **Heavy:** yes. **Cold read:** yes, and the reviewer checks one thing: that no mutating test ended up sharing a world. A shared world that a grant-mutating test changes would make the authorization matrix order-dependent, and it could pass for the wrong reason.

**Out of scope:**
- Changing any assertion.
- Merging the overlapping tier and auth test files (the review's "Not now").
- Any product change.
