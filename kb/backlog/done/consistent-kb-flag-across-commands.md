---
id: consistent-kb-flag-across-commands
title: "Make -k flag work consistently across all commands that accept a KB name"
type: backlog_item
tags: [cli, ux, consistency]
importance: 5
kind: bug
status: done
priority: low
effort: S
rank: 0
---

## Problem

`pyrite search` accepts `-k` / `--kb` as a flag for filtering by KB name. But `pyrite index sync` takes the KB name as a positional argument only -- `-k` is not recognized. This inconsistency is a paper cut when switching between commands.

## Expected Behavior

Every command that accepts a KB name should accept both `-k <name>` and a positional argument, or at minimum the `-k` shorthand should work everywhere.

## Reproduction

```bash
pyrite search "test" -k cascade-timeline    # works
pyrite index sync -k cascade-timeline       # fails: "No such option: -k"
pyrite index sync cascade-timeline          # works
```

## Resolution (2026-06-22)

The original repro (`index sync -k`) now works — `index sync` and the other
common read/index commands (search, get, index embed, tags, backlinks,
task list, task get) all accept `-k`/`--kb`. Verified and locked with a
contract test: tests/test_cli_kb_flag_consistency.py.

Commands that take a single *required* KB as a positional argument
(`kb info/remove`, `qa assess/stale/...`, `index reconcile`, `task migrate`)
are intentionally left positional — that is their established convention and
converting required positionals to options would break existing callers and
scripts for no real ergonomic gain on those rarely-chained commands.
