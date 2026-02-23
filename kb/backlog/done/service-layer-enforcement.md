---
type: backlog_item
title: "Route All Data Access Through Service Layer"
kind: improvement
status: proposed
priority: high
effort: M
tags: [architecture, refactoring, quality]
---

## Summary

CLI commands, API endpoints, and MCP tool handlers bypass `KBService` and access `PyriteDB` / `KBRepository` directly. This means hooks don't fire, validation can be skipped, and behavior is inconsistent across interfaces.

## Current State (from architecture review)

- **CLI**: 8 direct DB accesses, 4 direct Repo accesses
- **Endpoints**: 3 direct Repo accesses, raw SQL in entries.py (titles/resolve)
- **MCP**: 1 direct DB access, 4 direct Repo accesses

## Fix

Make `KBService` the sole interface for data operations:

1. Add convenience methods to KBService for endpoint queries (`list_titles()`, `resolve_entry()`)
2. CLI commands call KBService instead of instantiating PyriteDB/KBRepository
3. Endpoints call KBService instead of accessing storage directly
4. MCP handlers call KBService instead of accessing storage directly

## Acceptance Criteria

- [ ] No direct PyriteDB or KBRepository usage outside of KBService and storage layer
- [ ] entries.py `list_entry_titles` and `resolve_entry` use service methods, not raw SQL
- [ ] CLI create/update/delete go through KBService (hooks fire)
- [ ] MCP create/update/delete go through KBService
- [ ] All existing tests pass
