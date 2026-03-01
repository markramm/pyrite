---
id: architecture-hardening
title: "Architecture Hardening"
type: backlog_item
tags:
- improvement
- security
- architecture
- code-hardening
kind: improvement
priority: high
effort: M
status: done
links:
- roadmap
---

# Architecture Hardening

**Wave 8 of 0.9 Code Hardening.** Security fixes, constant extraction, layer violation fixes, and documentation cleanup.

## Items

| Item | Files | Effort | Description |
|------|-------|--------|-------------|
| Validate plugin DDL inputs | `storage/connection.py` | S | Prevent SQL injection in plugin-provided DDL by validating table/column names against allowlist pattern |
| Extract hardcoded constants | `mcp_server.py` | S | Extract URI scheme prefix and magic number 50 (bulk create limit) into named constants |
| Fix storage→service layer violation | `storage/index.py` | S | `IndexManager` calls service-layer methods directly — route through proper layer boundary |
| Consolidate/delete stale docs/ directory | `docs/` | M | Audit `docs/` for stale content, consolidate useful docs into `kb/`, delete remainder |

## Resolution

| Item | Status | Notes |
|------|--------|-------|
| Validate plugin DDL inputs | **Done** | Added `_VALID_SQL_DEFAULT` regex to `connection.py` — allows NULL, TRUE/FALSE, CURRENT_TIMESTAMP, numbers, quoted strings. 15 parametrized tests. |
| Extract hardcoded constants | **Done** | Added `MAX_BULK_CREATE_ENTRIES = 50` constant in `mcp_server.py`, replaced magic number. |
| Fix storage→service layer violation | **No action** | `GitService` is pure git plumbing, not a service-layer concern. The duck-typed `Any` parameter is fine. |
| Consolidate/delete stale docs/ directory | **No action** | No `docs/` directory exists — already cleaned up. |
