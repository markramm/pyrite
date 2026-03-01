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
status: planned
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

## Definition of Done

- Plugin DDL inputs validated (table names match `^[a-z_][a-z0-9_]*$`)
- No magic numbers in MCP server — all constants named and documented
- No storage→service layer violations (storage only calls storage)
- `docs/` directory either consolidated or deleted, no stale content
