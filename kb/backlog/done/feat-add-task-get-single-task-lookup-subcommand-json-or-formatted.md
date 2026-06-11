---
id: feat-add-task-get-single-task-lookup-subcommand-json-or-formatted
type: backlog_item
title: "CLI feature (re-filed from cascade-research, originally observed across conductor sessions)"
kind: feature
status: superseded
priority: medium
effort: S
tags: [bug, conductor-filed, cli, task-system]
---

CLI feature (re-filed from cascade-research, originally observed across conductor sessions). 'pyrite task get <id>' returns 'No such command get'. Available: task list/claim/update/create. Need a single-task full-state lookup (status, assignee, body, work-log) for conductor QC + reconciliation before deciding to close. Workaround today: Read the task file directly (bypasses pyrite status logic) or 'task list --status X' + filter. PROPOSED: 'pyrite task get <id> -k <kb>' returning full state as JSON or formatted text. IMPORTANT (see sibling bug-task-status-single-item-json-read): ensure 'task get' reads the SAME consistent path as 'task list' so it can't lag a recent claim. Owner: pyrite repo (git@github.com/markramm/pyrite). Re-filed from cascade-research/notes/issue-pyrite-cli-missing-task-get-subcommand.

## PO triage note (2026-06-10)

**Superseded by
[[bug-task-status-single-item-json-read-intermittently-empty-while-list-view-correct]].**

`pyrite task status <id>` already exists and does what this ticket asks
("Show task details with children, dependencies, and evidence"). The
conductor's "task get returns 'No such command'" observation was actually
a discovery of the missing command name — but the functional command
exists under `task status`. The intermittent-empty-JSON bug in
`task status` is the real issue.

The fix for the read-path bug (bug-task-status-single-item-json-read-...)
now includes renaming `task status` → `task get` to match the convention
this feature ticket asked for. So this feature's intent is fully covered
by that bug's fix; no separate work needed.

