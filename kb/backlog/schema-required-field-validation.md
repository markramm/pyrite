---
id: schema-required-field-validation
type: backlog_item
title: "Validate required fields against kb.yaml schema on index"
kind: feature
status: proposed
priority: medium
effort: M
tags: [robustness, schema, health-check]
---

`kb.yaml` type declarations include `required:` lists, but nothing verifies
that entries actually have those fields. An entry of `type: timeline_event`
missing `date:` loads successfully, indexes, and silently breaks any
date-sorted view.

## Change

During index, for each entry whose type has a `required:` list in
`kb.yaml`, check that each required field is present and non-empty.
Emit per-entry warnings with:

- KB name
- entry id
- entry type
- missing field names

Surface through `pyrite index health` as a new field:

```json
{
  "missing_required_fields": [
    {
      "kb": "cascade-timeline",
      "id": "...",
      "type": "timeline_event",
      "missing": ["date"]
    }
  ]
}
```

## TDD

Failing test: KB with `timeline_event` declaring `required: [date, title]`,
an entry missing `date`, `index health` returns the entry in
`missing_required_fields`.

Depends on: [[warn-on-undeclared-entry-type]] (shared health-check
infrastructure).
