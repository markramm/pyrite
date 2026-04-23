---
id: warn-on-missing-type-fallback
type: backlog_item
title: "Warn when an entry is missing `type:` and defaults to note"
kind: feature
status: proposed
priority: medium
effort: S
tags: [robustness, schema]
---

Today when an entry's frontmatter lacks `type:`, pyrite silently defaults
to `NoteEntry` (or `GenericEntry`). This is how 302 cascade-timeline
entries were misclassified and dropped from the viewer export.

## Change

In the entry factory path (`entry_from_frontmatter` in
`pyrite/models/core_types.py`), when `meta.get("type")` is falsy and the
fallback is taken, log a structured warning with the file path and the
type that was assumed. Don't raise — preserve current behavior for code
flexibility — but make the fallback visible.

Bonus: surface the count through `pyrite index health` as
`type_fallbacks: N` so this isn't just a log line.

## TDD

Failing test: load an entry with frontmatter `id: x\ntitle: y` (no type),
assert a warning is logged identifying the file and the fallback type.
