---
id: task-list-priority-range-filter
type: backlog_item
title: "Support priority range filters on `pyrite task list` (e.g., `--priority 7+`, `--priority 7-9`)"
kind: feature
status: proposed
priority: low
effort: S
tags: [task-system, cli, ux, conductor-workflow, query]
---

## Problem

`pyrite task list --priority N` accepts exact-match priority filtering, but the conductor workflow routinely needs **range filters**: "all P7+" or "all P8-P9" for dispatch-eligibility queries.

Documented session friction (2026-06-02): the investigation-conductor's stop-condition check needs `open_priority_7_plus` — currently computed by piping `pyrite task list --format json` through Python:

```bash
pyrite task list -k cascade-research --format json | python3 -c "
import json, sys
r = json.load(sys.stdin)
tasks = r.get('tasks', r) if isinstance(r, dict) else r
open_p7 = [t for t in tasks if t.get('status')=='open' and (t.get('priority') or 0) >= 7]
print(len(open_p7))
"
```

This works but is verbose, error-prone (the `or 0` handling for null-priority is non-obvious), and forces shell pipelines through Python for what should be a CLI flag.

Additionally: this session tried `--priority 8` mid-loop and the CLI changed output format unexpectedly (or rejected the flag — pattern wasn't clear). Range filters would benefit from a coherent design pass.

## Proposed solution

Support shorthand range syntax on `--priority`:

```
pyrite task list -k cascade-research --priority 7+ --status open  # P7-P10
pyrite task list -k cascade-research --priority 7-9 --status open  # P7-P9 inclusive
pyrite task list -k cascade-research --priority 7 --status open    # exact P7 (existing behavior)
pyrite task list -k cascade-research --priority <8 --status open   # below P8 (P1-P7)
```

Parsing:
- `N` → exact match (current)
- `N+` → ≥N
- `N-` → ≤N
- `N-M` → range [N, M] inclusive
- `<N` / `>N` → strict
- `<=N` / `>=N` → inclusive

## Related

- `task-list-age-filter.md` — adjacent CLI-quality-of-life addition
- The broader pattern: `pyrite task list` could benefit from a more expressive query language across all filterable fields (priority, age, assignee-prefix, tag-match). See if a single design pass on `task list --query` would be cheaper than per-flag accretion.

## Effort

S — argument parser + filter logic. Trivial if no broader query-language redesign is in scope.
