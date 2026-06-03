---
id: task-bulk-update-by-filter
type: backlog_item
title: "Add `pyrite task bulk-update` (or `--filter` flag) for one-command status sweeps"
kind: feature
status: proposed
priority: medium
effort: M
tags: [task-system, cli, conductor-workflow, grooming, bulk-operations]
---

## Problem

The investigation-conductor's grooming work routinely walks 3–10 tasks through the same state transition for the same reason. Per the state machine, each transition requires a separate `pyrite task update` invocation; for tasks moving from `in_progress` → `done`, agents typically need to walk through an intermediate state (3 commands per task), yielding 9–30 commands per grooming pass.

Documented session friction (2026-06-02):

- **9 stale-claim sweep** (Colson / Constellis / Phelan / Vance-AI / Cyber Apex / Gould-Bitfury / 8VC-Taiwan / inv6-datacenter / Phase-N): 27 individual commands to walk through state machine
- **GENIUS Act dedupe** (3 duplicate parents): 9 individual commands
- **Two WLTC monitor closures** (deliverable-complete, watch-window-passed): 6 individual commands

Total: 42 commands in one grooming pass that semantically were three batch operations.

## Proposed solution

Add bulk-update mechanism. Two design options:

**Option A: `pyrite task bulk-update` subcommand**
```
pyrite task bulk-update -k cascade-research \
  --filter "assignee:agent:claude-*-parallel-tick* AND status:in_progress AND age>2h" \
  --status done \
  --comment "stale-sweep audit 2026-06-02"
```

**Option B: `--filter` flag on existing `update`**
```
pyrite task update -k cascade-research \
  --filter "assignee:agent:claude-*-parallel-tick* AND status:in_progress AND age>2h" \
  --status done \
  --comment "stale-sweep audit 2026-06-02"
```

Either way:
- Filter supports basic query language (status / priority / assignee / age / tag patterns)
- Dry-run mode (`--dry-run`) shows which tasks would be affected before commit
- Honors state-machine rules (rejects bulk transition if any target task can't make the move; report which)
- Single git commit per bulk operation (cleaner audit trail than 42 commits)
- Comment from `--comment` flag (see `task-update-comment-flag.md`) propagates to every affected task

## Related

- `task-update-comment-flag.md` — comment-on-transition feature pairs naturally with bulk-update
- `add-task-reset-command-for-stale-claims.md` — narrower scope; bulk-update generalizes it
- `web-ui-bulk-operations.md` — same need at web-UI layer

## Effort

M — filter parser + dry-run mode + per-target state-machine validation + atomic commit. Non-trivial because of state-machine validation, but the building blocks exist.
