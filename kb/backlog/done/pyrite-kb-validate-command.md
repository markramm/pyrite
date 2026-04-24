---
id: pyrite-kb-validate-command
title: "Add `pyrite kb validate` CLI command"
type: backlog_item
tags: [cli, robustness, dx]
links:
- target: epic-normalization-and-data-cleanup
  relation: subtask_of
  kb: pyrite
importance: 5
kind: feature
status: completed
priority: medium
effort: S
rank: 0
---

Consolidate the new index-time warnings into one on-demand validation
command so users don't have to parse index-build stderr to learn about
data problems.

## Change

Add `pyrite kb validate [-k KB]` that runs:

- Undeclared-type check ([[warn-on-undeclared-entry-type]])
- Missing-type fallback check ([[warn-on-missing-type-fallback]])
- Required-field check ([[schema-required-field-validation]])
- Existing `index health` checks (missing files, unindexed, stale, broken
  links)

Output a structured JSON report suitable for scripting, with a
human-friendly mode when stdout is a TTY.

Exit code: 0 if clean, 1 if any errors, 2 if only warnings. Good for CI.

Depends on: the three warning-producing backlog items above.
