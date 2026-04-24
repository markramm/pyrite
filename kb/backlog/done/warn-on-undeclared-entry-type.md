---
id: warn-on-undeclared-entry-type
title: "Warn when entry type is not declared in kb.yaml"
type: backlog_item
tags: [robustness, schema, health-check]
links:
- target: epic-normalization-and-data-cleanup
  relation: subtask_of
  kb: pyrite
importance: 5
kind: feature
status: completed
priority: high
effort: S
rank: 0
---

Today `pyrite index build` silently accepts entries with any `type:`
value. An entry with `type: timeline_event` indexes fine even if the KB's
`kb.yaml` only declares `type: event`. This is how cascade-timeline drift
went undetected for weeks.

## Change

On index, for each entry whose `entry_type` is not in
`config.kb_schema.types`, emit a structured warning. Don't fail — the
indexer should still accept the entry so tooling can run — but surface
the mismatch.

Surface the warning through `pyrite index health` as a new field:

```json
{
  "status": "warning",
  "undeclared_types": [
    {"kb": "cascade-timeline", "type": "timeline_event", "count": 4886}
  ]
}
```

## TDD

Failing test: a KB with `kb.yaml` declaring only `event`, an entry with
`type: timeline_event`, and a call to `index health` — expect the new
`undeclared_types` field to contain `timeline_event`.

Related: would have caught today's cascade drift immediately.
