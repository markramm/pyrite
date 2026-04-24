---
id: schema-required-field-validation
title: "Validate required fields and subdirectory placement against kb.yaml schema on index"
type: backlog_item
tags: [robustness, schema, health-check]
links:
- target: epic-normalization-and-data-cleanup
  relation: subtask_of
  kb: pyrite
importance: 5
kind: feature
status: completed
priority: medium
effort: M
rank: 0
---

`kb.yaml` type declarations include `required:` lists and `subdirectory:`
hints, but nothing verifies either at read time. An entry of
`type: timeline_event` missing `date:` loads successfully, indexes, and
silently breaks any date-sorted view. An entry whose type declares
`subdirectory: events` but lives at the KB root is silently accepted —
the reader uses `rglob("*.md")`.

## Change

Two related index-time checks:

### Required-field check

For each entry whose type has a `required:` list in `kb.yaml`, check
that each required field is present and non-empty. Emit per-entry
warnings with KB name, entry id, entry type, missing field names.

### Subdirectory-mismatch check

Decision: `subdirectory:` stays a writer hint, not a reader constraint
(supersedes [[clarify-subdirectory-handling]]). The reader continues
to accept any layout. But on index, warn when an entry's file path
doesn't match the declared subdirectory for its type — surfaces
layout drift without breaking existing KBs.

### Health output

Surface both through `pyrite index health` as new fields:

```json
{
  "missing_required_fields": [
    {
      "kb": "cascade-timeline",
      "id": "...",
      "type": "timeline_event",
      "missing": ["date"]
    }
  ],
  "subdirectory_mismatches": [
    {
      "kb": "cascade-timeline",
      "id": "...",
      "type": "timeline_event",
      "declared_subdirectory": "events",
      "actual_path": "."
    }
  ]
}
```

## TDD

1. `test_missing_required_field_surfaces_in_health` — KB with
   `timeline_event` declaring `required: [date, title]`, entry missing
   `date`, `index health` returns the entry in `missing_required_fields`.
2. `test_subdirectory_mismatch_surfaces_in_health` — KB with
   `timeline_event` declaring `subdirectory: events`, entry living at
   the KB root, `index health` returns the entry in
   `subdirectory_mismatches`.

## Depends on

[[warn-on-undeclared-entry-type]] (shared health-check infrastructure).
