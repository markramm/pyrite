---
id: test-evidence-per-hunk-revert-automates-the-guards-rule
title: "Test evidence phase 2: per-hunk revert automates the guards rule (#360)"
type: backlog_item
tags:
- quality
- test
- process
kind: feature
status: proposed
priority: medium
effort: M
milestone: "0.27"
---

## Why
Approved by the maintainer on 2026-09-25 for 0.27. The guards rule (#360) says every check has a test that fails when that check alone is removed. Workers run it by hand now: T1 removed 29 guards one at a time and #377 about 25, each with a test re-run and a written account. That costs a lot of tokens and suite time, and it is model output again.

Once red-green runs on a throwaway tree (`test-evidence-diff-coverage-and-red-green-on-a-throwaway-tree`), reverting one hunk at a time is just a loop: mutation testing restricted to what the PR changed.

## Acceptance (draft; groom after phase 1 lands)
- `verify-red --per-hunk` reverts each changed code hunk alone in the throwaway tree and runs the PR's new tests. It reports hunks that no test notices.
- Runs by PR label (`verify: per-hunk`) or nightly on dev. It starts with auth, storage and guard code.
- A hunk may be marked as intentionally untested (logging, docs) with a reason.
- Worker reports replace hand-written guards lists with the tool's table.
