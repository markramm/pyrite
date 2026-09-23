---
id: cli-help-assertions-fail-only-in-ci-one-plain-help-helper-and-a-guard
title: 'CLI --help assertions pass locally and fail only in CI: one shared plain-text helper, and a guard so new tests use it'
type: backlog_item
kind: quality
tags:
- quality
- testing
- contributors
status: proposed
priority: medium
effort: S
---

## Problem

A test that runs `pyrite <cmd> --help` through Typer's `CliRunner` and asserts
`"--flag" in result.stdout` passes in a plain local terminal and fails on
GitHub's runners. When the environment looks colour-capable, Rich styles each
option as two spans (`\x1b[1;36m-\x1b[0m\x1b[1;36m-flag\x1b[0m`), so the
literal `--flag` never appears contiguously even though it is plainly rendered.
`NO_COLOR=1` does not help (`FORCE_COLOR`/`TERM` win in Rich's precedence).

**It cost two first-time contributors a red gate on the same day (2026-09-23):**
#317 (`test_task_list_help_includes_priority`) and #318
(`test_task_create_help_lists_tags_option`). Both implementations were correct;
both authors ran their focused tests green; the conductor's own review of #317
passed for the same reason. Reproduce with `FORCE_COLOR=1 pytest <file>`.

`tests/test_cli_kb_flag_consistency.py:27-36` hit it first and carries a private
`_plain()` helper with a comment explaining the trap. Nothing points a newcomer
to it, and the good-first-issue template for #308/#309 told contributors to add
a `--help` test without mentioning it.

## Acceptance

- One shared helper (e.g. `plain(text)` in a `tests/` helper module or a
  `cli_help` fixture in `tests/conftest.py` returning ANSI-stripped help for an
  argv) — `test_cli_kb_flag_consistency.py`, #317's and #318's tests use it.
- A guard that fails on the pattern, not on the weather: either the suite's
  `CliRunner` invocations run with colour forced (so the trap fails locally
  too), or a structural test flags `"--…" in result.stdout/output` assertions
  that do not go through the helper. Pick the one that is cheaper to keep true;
  forcing colour everywhere must not break unrelated tests (measure: the
  2026-09-23 full run of #318 under `FORCE_COLOR=1` is the baseline).
- The good-first-issue groom standard (pyrite-conductor SKILL.md, groom lane)
  and CONTRIBUTING's testing section name the helper when an issue asks for a
  `--help` test.

## Out of scope

Changing how the CLI renders help for real users.
