---
type: component
title: "REST API Server"
kind: service
path: "pyrite/server/"
owner: "markr"
dependencies: ["fastapi", "slowapi", "pydantic", "pyrite.storage", "pyrite.config"]
tags: [core, api, server, fastapi]
---

# REST API Server

The REST API provides HTTP access to knowledge bases for the web frontend and external integrations. Built with FastAPI, all endpoints are served under the `/api` prefix.

## Architecture

```
pyrite/server/
  api.py                    # Factory, shared dependencies, rate limiter (~169 lines)
  endpoints/
    __init__.py             # Collects all routers into all_routers list
    kbs.py                  # GET /api/kbs
    search.py               # GET /api/search
    entries.py              # CRUD /api/entries, /entries/titles, /entries/resolve
    timeline.py             # GET /api/timeline
    tags.py                 # GET /api/tags
    admin.py                # GET /api/stats, POST /api/index/sync, GET /api/ai/status
    starred.py              # CRUD /api/starred
    templates.py            # /api/kbs/{kb}/templates
  schemas.py                # Pydantic request/response models
  static.py                 # Static file serving for SvelteKit dist
  mcp_server.py             # MCP server (separate from REST API)
```

## Key Design Decisions

### Endpoint module pattern

Each endpoint module creates its own `APIRouter` with a tag for OpenAPI grouping. Shared dependencies (`get_config`, `get_db`, `get_index_mgr`, `verify_api_key`, `limiter`) stay in `api.py` and are imported by endpoint modules. The application factory in `api.py` collects all routers under a parent `/api` router with auth dependency.

This pattern was adopted to eliminate `api.py` as a merge bottleneck when multiple agents work in parallel — agents working on starred entries never touch the same file as agents working on templates.

### Dependency injection

FastAPI's `Depends()` system is used for config, database, and index manager injection. Module-level singletons with lazy initialization:

- `get_config()` — loads `PyriteConfig` from config file
- `get_db()` — creates `PyriteDB` connection
- `get_index_mgr()` — creates `IndexManager` with db and config

Tests override these globals directly via `api_module._config = ...`.

### Rate limiting

slowapi with `get_remote_address` key function. Read endpoints: 100/minute. Write endpoints: 30/minute. Health check is not rate-limited (infra probes).

### Authentication

Optional API key via `X-API-Key` header or `api_key` query param. When `config.settings.api_key` is empty, auth is disabled (backwards-compatible).

### CORS

Configured from `config.settings.cors_origins`. Credentials disabled when wildcard origin is used (spec compliance).

## Endpoint Summary

| Endpoint | Method | Module | Description |
|----------|--------|--------|-------------|
| `/api/kbs` | GET | kbs.py | List knowledge bases |
| `/api/search` | GET | search.py | Full-text search (keyword/semantic/hybrid) |
| `/api/entries` | GET | entries.py | Paginated entry listing |
| `/api/entries/titles` | GET | entries.py | Lightweight autocomplete data |
| `/api/entries/resolve` | GET | entries.py | Wikilink target resolution |
| `/api/entries/{id}` | GET | entries.py | Get entry by ID |
| `/api/entries` | POST | entries.py | Create entry |
| `/api/entries/{id}` | PUT | entries.py | Update entry |
| `/api/entries/{id}` | DELETE | entries.py | Delete entry |
| `/api/timeline` | GET | timeline.py | Timeline events |
| `/api/tags` | GET | tags.py | Tags with counts |
| `/api/stats` | GET | admin.py | Index statistics |
| `/api/index/sync` | POST | admin.py | Trigger incremental sync |
| `/api/ai/status` | GET | admin.py | AI/LLM provider status |
| `/api/starred` | GET/POST | starred.py | List/star entries |
| `/api/starred/{id}` | DELETE | starred.py | Unstar entry |
| `/api/starred/reorder` | PUT | starred.py | Reorder starred entries |
| `/api/kbs/{kb}/templates` | GET | templates.py | List templates |
| `/api/kbs/{kb}/templates/{name}` | GET | templates.py | Get template detail |
| `/api/kbs/{kb}/templates/{name}/render` | POST | templates.py | Render template |
| `/health` | GET | api.py | Health check (not behind /api) |

## Adding New Endpoints

1. Create a new module in `pyrite/server/endpoints/` with its own `APIRouter`
2. Import request/response models from `../schemas.py` (add new ones there)
3. Import shared deps from `..api` (`get_config`, `get_db`, `limiter`, etc.)
4. Add the router import to `endpoints/__init__.py`'s `all_routers` list
5. Write tests — the test pattern uses `TestClient(app)` with injected globals

## Related

- [ADR-0007](../adrs/0007-ai-integration-architecture.md) — AI integration architecture
- [ADR-0010](../adrs/0010-content-negotiation-and-format-support.md) — Content negotiation
- [MCP Server](mcp-server.md) — The other server interface (MCP tools)
- [Storage Layer](storage-layer.md) — PyriteDB that endpoints query
