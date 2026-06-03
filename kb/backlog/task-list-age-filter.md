---
id: task-list-age-filter
type: backlog_item
title: "Add `--age` filter to `pyrite task list` for stale-claim detection without shell date math"
kind: feature
status: proposed
priority: low
effort: S
tags: [task-system, cli, conductor-workflow, stale-recovery, query]
---

## Problem

The investigation-conductor's stale-claim sweep (`SKILL.md` Step 4) requires identifying tasks whose notes-file mtime is older than 2 hours AND whose status is `in_progress` AND whose assignee starts `agent:claude-*`. The age-comparison step currently requires shell date math:

```bash
pyrite task list -k cascade-research --status in_progress --format json | python3 -c "
import json, sys, os, datetime
r = json.load(sys.stdin)
tasks = r.get('tasks', r) if isinstance(r, dict) else r
now = datetime.datetime.now()
for t in tasks:
    f = f'cascade-research/notes/{t.get(\"id\", \"\")}.md'
    age_h = (now - datetime.datetime.fromtimestamp(os.path.getmtime(f))).total_seconds() / 3600 if os.path.exists(f) else 999
    # ... filter on age_h ...
"
```

This works but is fragile (relies on notes-file existing at predictable path; depends on Python availability; doesn't fit in shell-native pipelines).

## Proposed solution

Add `--age` filter accepting duration shorthand:

```
pyrite task list -k cascade-research --status in_progress --age '>2h'
pyrite task list -k cascade-research --status open --age '<24h'
pyrite task list -k cascade-research --status in_progress --age '>4d'
```

Duration parsing:
- `Ns` / `Nm` / `Nh` / `Nd` for seconds / minutes / hours / days
- Comparison operators `>` / `<` / `>=` / `<=`
- "Age" defined as: time since last status transition (or, optionally, time since notes-file mtime if that's the canonical signal)

The right age-source needs a design decision: status-transition-time is cleaner conceptually but currently isn't stored on the task record (see `task-update-comment-flag.md`'s proposed `status_change_log`). Notes-file mtime is the current signal but is an implementation detail.

## Related

- `task-update-comment-flag.md` — if status_change_log lands, age becomes a clean derived field
- `add-task-reset-command-for-stale-claims.md` — age-filter is a building block for stale-claim detection
- `task-bulk-update-by-filter.md` — paired use case: filter by age, bulk-walk to done

## Effort

S — once age-source is decided. The comparison parsing is straightforward.
