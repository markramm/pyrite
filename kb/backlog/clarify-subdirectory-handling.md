---
id: clarify-subdirectory-handling
type: backlog_item
title: "Decide and document subdirectory handling for entries"
kind: chore
status: proposed
priority: low
effort: S
tags: [schema, docs, cascade]
---

`repo.list_files()` uses `rglob("*.md")` and silently accepts any layout.
`kb.yaml` type declarations have a `subdirectory:` field that the writer
path uses when creating entries, but the reader doesn't enforce it.

Cascade-timeline demonstrates the confusion: 4838 entries at the KB root,
25 entries in an `events/` subdirectory that nobody expected. The reader
picked them up fine; the human mental model didn't match.

## Decide

Two options:

1. **Strict**: enforce subdirectory on read. An entry whose type declares
   `subdirectory: events` but lives at the root is a warning. Use
   `pyrite index reconcile` to auto-move misplaced files.

2. **Flexible**: keep current behavior, document it clearly in the KB
   schema docs. `subdirectory:` is a writer hint, not a reader constraint.
   Warn on mismatch but don't enforce.

Recommendation: option 2 (flexible). Less ceremony, matches current code.
But the *decision* and the *documentation* both need to happen.

## Change

Once decided:
- Update `docs/` schema docs with the chosen behavior
- Add a health-check warning for misplaced files (under either option)
- Optionally: add a `pyrite index reconcile --dry-run` that shows what
  would move under strict mode, even if the default stays flexible
