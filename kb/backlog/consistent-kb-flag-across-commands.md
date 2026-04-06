---
id: consistent-kb-flag-across-commands
type: backlog_item
title: "Make -k flag work consistently across all commands that accept a KB name"
kind: bug
status: proposed
priority: low
effort: S
tags: [cli, ux, consistency]
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
