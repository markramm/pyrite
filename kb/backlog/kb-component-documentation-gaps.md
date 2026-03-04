---
id: kb-component-documentation-gaps
type: backlog_item
title: "Fill KB component documentation gaps for undocumented modules"
kind: improvement
status: proposed
milestone: "0.17"
priority: medium
effort: M
tags: [documentation, kb, architecture]
---

# Fill KB component documentation gaps for undocumented modules

## Problem

The KB documents 33 components but roughly 20+ significant modules have no component entry. Critical interface contracts (`SearchBackend` protocol, `PyritePlugin` protocol, `KBRepository`, `IndexManager`) are undocumented. 6 existing component entries point to directories rather than specific files, providing no architectural information.

## Missing component entries

### Critical (interface contracts)

| Module | Why it matters |
|--------|---------------|
| `pyrite/storage/backends/protocol.py` | `SearchBackend` protocol — defines SQLite/Postgres contract |
| `pyrite/plugins/protocol.py` | `PyritePlugin` protocol — entire extension surface |
| `pyrite/storage/repository.py` | `KBRepository` — file I/O for entries |
| `pyrite/storage/index.py` | `IndexManager` — index sync orchestration |

### Services

| Module | Notes |
|--------|-------|
| `pyrite/services/repo_service.py` | Multi-repo management |
| `pyrite/services/template_service.py` | Entry templates and presets |
| `pyrite/services/query_expansion_service.py` | Query expansion for search |
| `pyrite/services/oauth_providers.py` | OAuth provider implementations |

### Storage internals

| Module | Notes |
|--------|-------|
| `pyrite/storage/migrations.py` | Schema migrations |
| `pyrite/storage/backends/sqlite_backend.py` | SQLite search backend |
| `pyrite/storage/backends/postgres_backend.py` | Postgres search backend |

### Server

| Module | Notes |
|--------|-------|
| `pyrite/server/auth_endpoints.py` | Auth routes (outside /api) |
| `pyrite/server/schemas.py` | Pydantic response models |
| `pyrite/server/tool_schemas.py` | MCP tool definitions |
| 16 of 17 endpoint modules | Only `blocks.py` is documented |

### Hollow stubs to flesh out

These exist but point to directories with no useful content:
- "Collaboration Services" → `pyrite/services/`
- "REST API Server" → `pyrite/server/`
- "Storage Layer" → `pyrite/storage/`
- "CLI System" → `pyrite/cli/`
- "Entry Model" → `pyrite/models/`
- "Plugin System" → `pyrite/plugins/`

## Solution

1. Create component entries for the 4 critical interface contracts first
2. Flesh out the 6 hollow directory-level stubs with actual architecture info
3. Add service component entries (4 services)
4. Add storage and server component entries as time permits

Use the CLI:
```bash
.venv/bin/pyrite create -k pyrite -t component --title "SearchBackend Protocol" \
  -b "..." --tags core,storage
```

## Success criteria

- All 4 critical interface contracts have component entries
- 6 directory-level stubs replaced with useful architectural documentation
- `pyrite sw components` output matches actual codebase structure
- Each component entry includes: kind, path, owner, dependencies, and interface description
