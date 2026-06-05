# Pyrite Architecture: Key Source Files

Reference map of the core modules. Consult this when planning a change to know where to look first; SKILL.md keeps the architectural *decisions* (ADRs + 6 plugin integration points) since those affect process choices on every task.

## Plugins

| File | Purpose |
|------|---------|
| `pyrite/plugins/protocol.py` | `PyritePlugin` Protocol (15 methods + `name` attribute) |
| `pyrite/plugins/registry.py` | Plugin discovery and aggregation |

## Models & Schema

| File | Purpose |
|------|---------|
| `pyrite/models/core_types.py` | 9 built-in entry types + `ENTRY_TYPE_REGISTRY` |
| `pyrite/models/factory.py` | Entry factory — `build_entry()` single dispatch point |
| `pyrite/schema/` | `KBSchema`, `FieldSchema` — schema-as-config validation (6 submodules) |
| `pyrite/config.py` | `PyriteConfig`, `Settings`, `KBConfig` |

## CLI

| File | Purpose |
|------|---------|
| `pyrite/cli/__init__.py` | Main Typer CLI app, all commands |

## Storage

| File | Purpose |
|------|---------|
| `pyrite/storage/database.py` | `PyriteDB` (SQLite + FTS5) |
| `pyrite/storage/queries.py` | SQL queries (FTS search, tag search, graph) |

## Server (REST + MCP)

| File | Purpose |
|------|---------|
| `pyrite/server/api.py` | REST API factory, deps, rate limiter, central `PyriteError` handler |
| `pyrite/server/endpoints/` | Per-feature endpoint modules (kbs, search, entries, etc.) |
| `pyrite/server/mcp_server.py` | MCP server (3-tier tools) |

## Services

| File | Purpose |
|------|---------|
| `pyrite/services/kb_service.py` | `KBService` CRUD with hooks |
| `pyrite/services/search_service.py` | `SearchService` — keyword, semantic, hybrid search + RRF |
| `pyrite/services/embedding_service.py` | `EmbeddingService` — vector storage, similarity search |
| `pyrite/services/embedding_worker.py` | `EmbeddingWorker` — background embedding pipeline |
| `pyrite/services/llm_service.py` | `LLMService` — provider-agnostic LLM abstraction |
| `pyrite/services/template_service.py` | `TemplateService` — entry templates and presets |
| `pyrite/services/git_service.py` | `GitService` — git operations, commit, diff |
| `pyrite/services/repo_service.py` | `RepoService` — multi-repo management |
| `pyrite/services/user_service.py` | `UserService` — user identity and auth |
| `pyrite/services/clipper.py` | `ClipperService` — web clipper |
| `pyrite/services/graph_service.py` | `GraphService` — graph/link queries (extracted from `KBService`) |
| `pyrite/services/export_service.py` | `ExportService` — KB export and git operations (extracted from `KBService`) |
| `pyrite/services/ephemeral_service.py` | `EphemeralKBService` — ephemeral KB lifecycle with TTL (extracted from `KBService`) |
| `pyrite/services/quota_service.py` | `QuotaService` — usage tier limit checks (extracted from `KBService`) |
| `pyrite/services/collection_query.py` | Collection query functions |
