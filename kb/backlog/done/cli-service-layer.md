---
type: backlog_item
title: "Route CLI Data Access Through Service Layer"
kind: improvement
status: done
priority: high
effort: M
tags: [architecture, refactoring, quality]
---

## Summary

CLI commands (`cli/__init__.py`, `read_cli.py`, `write_cli.py`, `admin_cli.py`, `cli/repo_commands.py`) bypass `KBService` and access `PyriteDB` / `KBRepository` directly. This means hooks don't fire, validation can be skipped, and behavior is inconsistent with the API and MCP interfaces.

This matters especially because AI agent tools (Claude Code, Gemini CLI, Codex) are a primary interface — the CLI is not just a human convenience tool, it's how agents orchestrate long-running research tasks. Divergence between CLI and API/MCP behavior creates subtle bugs in agent workflows.

## Current State (post-#47)

API endpoints and MCP handlers now route through KBService. CLI does not:

- **cli/__init__.py**: 8 direct `PyriteDB` instantiations, direct `repo.save()`, `repo.load()`, `repo.delete()` calls
- **read_cli.py**: 9 direct `db.` calls (get_entry, get_timeline, get_tags, get_backlinks, count_entries)
- **write_cli.py**: Same as read_cli.py plus direct repo CRUD
- **admin_cli.py**: 5 direct `PyriteDB` instantiations (mostly for index/migration ops — some are appropriate)
- **cli/repo_commands.py**: 2 direct db accesses including raw SQL

## Fix

1. Create a shared CLI helper that instantiates `KBService` from config (similar to how endpoints use `get_kb_service`)
2. Route all CLI entry CRUD through `KBService.create_entry()`, `update_entry()`, `delete_entry()`
3. Route all CLI read queries through `KBService` query methods (get_entry, get_timeline, get_tags, get_backlinks, list_entries, count_entries)
4. Keep direct DB access only for admin operations (migrations, index rebuild) where service layer is inappropriate

## Acceptance Criteria

- [x] CLI create/update/delete go through KBService (hooks fire)
- [x] CLI read queries use KBService methods
- [x] No direct PyriteDB/KBRepository usage in cli/__init__.py, read_cli.py, write_cli.py
- [x] admin_cli.py direct DB access limited to migration/index operations
- [x] All existing tests pass (456/456)
