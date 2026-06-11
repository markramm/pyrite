---
id: bug-task-status-single-item-json-read-intermittently-empty-while-list-view-correct
type: backlog_item
title: "READ-PATH INCONSISTENCY (investigation-conductor session 2026-06-10)"
kind: bug
status: proposed
priority: high
effort: S
tags: [bug, conductor-filed, cli, task-system]
rank: 1150
---

READ-PATH INCONSISTENCY (investigation-conductor session 2026-06-10). 'pyrite task status <id> --format json' intermittently returned empty/non-JSON for a task that 'pyrite task list --format json' reported correctly in the same moment — observed right after a claim transition. The list endpoint is the more reliable single-source read. Possibly a read-after-write timing window between the single-item and list code paths. Relates to the already-filed 'pyrite CLI missing task get subcommand' issue — if a proper 'task get' is added, ensure it reads the SAME consistent path as 'task list', not a separate one that can lag. Owner: pyrite repo. Reproduce: claim a task, immediately 'task status <id> --format json'.

## PO triage note (2026-06-10)

Triage decision per PO call: this bug subsumes the proposed
[[feat-add-task-get-single-task-lookup-subcommand-json-or-formatted]]
feature. The `task status <id>` command already exists and is intended
to be the "show task details with children, dependencies, and evidence"
single-item lookup — but it returns intermittent empty JSON. The
conductor session saw the empty output and concluded the command was
missing.

Fix scope therefore includes a **rename**: `pyrite task status` →
`pyrite task get`. The name `status` is misleading (sounds like just
the status field, not the full record); `get` mirrors the
`pyrite get` convention for entries and matches what the conductor
expected when it tried `task get`.

Acceptance criteria additions:
- `pyrite task get <id> -k <kb>` is the new name; reads the same path
  as `task list` to avoid the read-after-write timing window.
- `pyrite task status` aliases to `task get` for one release with a
  `DeprecationWarning`, then is removed.
- Regression test: claim a task, immediately call `task get <id>
  --format json`, assert non-empty parseable JSON with the new state.


## Audit note (2026-06-11) — needs better repro

Attempted to reproduce during the Tier A audit loop pass:

- `pyrite task status <id> --format json` returned full parseable JSON
  on a single try.

The conductor report described the bug as "intermittent" — a single
successful call doesn't disprove it. Likely candidates for the
intermittency:

- Read-after-write timing window between `task claim` (or
  `task update -s claimed`) and the subsequent `task status` — the
  conductor's repro spec calls this out.
- A specific edge case in `task status`'s JSON serialization that only
  hits some tasks (the ones with empty/null children, for instance).

Don't fix speculatively. Before working this ticket, get a deterministic
repro: instrument the conductor's actual call sequence and capture both
the empty-JSON case and the surrounding context. If the bug is genuinely
non-deterministic timing in the file-read path, the fix probably lands
naturally in the `task status` → `task get` rename + read-path
consolidation that's already in this ticket's acceptance criteria.
