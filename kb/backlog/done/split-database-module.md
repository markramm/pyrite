---
type: backlog_item
title: "Split database.py Into Focused Modules"
kind: improvement
status: done
priority: medium
effort: M
tags: [architecture, refactoring, quality]
---

## Summary

`pyrite/storage/database.py` is 996 lines with 10+ distinct responsibilities: connection setup, plugin table creation, ORM/session management, KB operations, entry CRUD, search queries, tag analytics, timeline queries, user management, and repository operations.

## Fix

Split into focused modules while keeping a facade for backwards compatibility:

```
pyrite/storage/
  database.py          # Facade: PyriteDB class re-exports, connection setup (~150 lines)
  crud.py              # Entry insert/update/delete
  queries.py           # Search, timeline, analytics, tags
  kb_ops.py            # KB registration and stats
  user_ops.py          # User management
  connection.py        # SQLite pragmas, WAL setup, plugin table creation
```

Also address:
- Resource management: wrap `_raw_conn.execute()` in context managers consistently
- 119-line `upsert_entry` function: split into `_upsert_entry_main()`, `_sync_tags()`, `_sync_sources()`, `_sync_links()`

## Acceptance Criteria

- [ ] database.py under 200 lines (facade only)
- [ ] Each new module under 300 lines
- [ ] No function over 60 lines
- [ ] All raw connection usage in context managers
- [ ] PyriteDB public API unchanged (backwards compatible)
- [ ] All existing tests pass
