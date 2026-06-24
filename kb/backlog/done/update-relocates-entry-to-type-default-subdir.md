---
id: update-relocates-entry-to-type-default-subdir
title: "Updating an entry relocates its file to the type-default subdir, ignoring deliberate placement"
type: backlog_item
tags: [storage, update, subdirectory, placement, data-integrity]
importance: 5
kind: bug
status: done
priority: high
effort: M
rank: 0
---

## Problem

Any `pyrite update` that changes a field re-saves the entry to its **type-default
subdirectory**, deleting the original file — even when the entry was deliberately
placed elsewhere. Observed repeatedly this session: marking a `backlog_item`
`status=done` moves `kb/backlog/<id>.md` → `kb/notes/<id>.md` (generic type default),
so every ticket close needs a manual `mv ... kb/backlog/done/` workaround (documented
in `.claude/skills/pyrite-dev/gotchas.md`). The same logic would relocate an ADR out of
`kb/adrs/` on a status update.

This is a data-placement bug: the file silently leaves the directory the user/convention
put it in. It is closely related to `[[duplicate-entry-ids-across-backlog-and-done]]`
(when the delete-old step fails or the paths race, you get two files with one id).

## Root cause

`DocumentManager.save_entry` (`pyrite/storage/document_manager.py`):

```python
old_path = repo.find_file(entry.id)      # current real location
file_path = repo.save(entry)             # re-infers subdir from TYPE DEFAULT
if old_path and old_path.resolve() != file_path.resolve():
    self._remove_old_file(old_path, ...)  # deletes the original
```

`repo.save(entry)` is called with no `subdir`, so `KBRepository.save`
(`repository.py:290`) falls through to `_infer_subdir(entry)`, which returns the type's
default subdirectory (`repository.py:179`) regardless of where the file currently lives.
The `old_path != file_path` cleanup then moves it.

The move is *intended* only for **templated** subdirectories (e.g. a type declaring
`subdirectory: backlog/{status}`, where a status change legitimately implies a new
folder). For static or unset subdirectories it is wrong — it overrides deliberate
placement.

## Fix

In `save_entry`, when the entry already exists on disk (`old_path` is set) AND the type's
declared `subdirectory` is NOT templated (no `{...}` placeholder), preserve the existing
location: derive the subdir from `old_path` relative to the KB root and pass it to
`repo.save(entry, subdir=...)`. Only re-infer (allowing the move) for new entries or
genuinely templated subdirectories.

Add regression tests: (a) updating a `backlog_item` in `kb/backlog/done/` keeps it there;
(b) an entry under a `backlog/{status}` templated subdir still moves on status change.

## Provenance

Hit on essentially every ticket completion during the 2026-06-23 pyrite-dev loop. Promoted
from the long-standing gotcha ("Not yet ticketed") to a high-priority bug because it
corrupts placement on a routine operation and is the single biggest friction in the
ticket workflow.
