---
id: task-claim-concurrency-test
type: backlog_item
title: "Execute the claim CAS concurrently: N processes race claim_task, exactly one wins"
kind: tech_debt
status: proposed
priority: high
effort: S
created: "2026-07-03"
tags: [testing, concurrency, tasks, agents, audit-2026-07]
links:
- target: epic-shared-instance-readiness
  relation: related
  kb: pyrite
---

## Problem

The task-claim compare-and-swap is the ONE concurrency guard the
entire multi-agent fleet depends on ("the one concurrency guard in
the whole system" per the investigation-research skill), and it has
never been executed concurrently: zero threading/multiprocessing/
concurrent.futures usage anywhere in tests/. `test_task_service.py:
313-360` tests claim conflicts only as sequential simulation (claim,
then second claim fails). The CAS design is correct
(`UPDATE ... WHERE status = :from_status` + rowcount check), but
SQLite-under-concurrent-writers behavior (WAL mode, busy timeouts,
connection-per-process) is exactly the kind of thing that differs
between "correct design" and "correct under load."

## Fix

- One test: N processes (not threads — agents are processes; use
  multiprocessing with separate connections) race `claim_task` on a
  single open task. Assert exactly one winner, N-1 clean
  CONFLICT-class failures (not exceptions, not corrupted rows), and
  the task file on disk matches the winner.
- Repeat for the release/reset path (stale-claim reset racing an
  active claimer).
- Run against both backends (postgres via the conformance fixture
  once [[ci-make-green-and-load-bearing]] adds the service
  container).

## Acceptance criteria

- The race test exists, runs in CI, and fails if the rowcount check
  is removed (verified by mutation once, in the PR description).
