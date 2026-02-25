---
type: component
title: "REST API Server"
kind: service
path: "pyrite/server/"
owner: "markr"
dependencies: ["fastapi", "slowapi", "pydantic", "pyrite.storage", "pyrite.config", "pyrite.services"]
tags: [core, api, server, fastapi]
---

# REST API Server

The REST API provides HTTP access to knowledge bases for the web frontend and external integrations. Built with FastAPI, all endpoints are served under the `/api` prefix.

## Architecture

```
pyrite/server/
  api.py                    # Factory, shared dependencies, rate limiter
  endpoints/
    __init__.py             # Collects all routers into all_routers list
    kbs.py                  # GET /api/kbs
    search.py               # GET /api/search (keyword/semantic/hybrid)
    entries.py              # CRUD /api/entries, /entries/titles, /entries/resolve
    timeline.py             # GET /api/timeline
    tags.py                 # GET /api/tags, /api/tags/tree
    admin.py                # Stats, sync, AI status, KB management, plugins
    ai_ep.py                # POST /api/ai/{summarize,auto-tag,suggest-links,chat}
    starred.py              # CRUD /api/starred
    templates.py            # /api/kbs/{kb}/templates
    daily.py                # /api/daily/{date}, /api/daily/dates
    settings_ep.py          # CRUD /api/settings
    versions.py             # GET /api/versions/{entry_id}
  schemas.py                # Pydantic request/response models
  websocket.py              # WebSocket connection manager for real-time events
  static.py                 # Static file serving for SvelteKit dist
  mcp_server.py             # MCP server (separate from REST API)
```

## Key Design Decisions

### Endpoint module pattern

Each endpoint module creates its own `APIRouter` with a tag for OpenAPI grouping. Shared dependencies (`get_config`, `get_db`, `get_index_mgr`, `get_kb_service`, `get_llm_service`, `verify_api_key`, `limiter`) stay in `api.py` and are imported by endpoint modules. The application factory in `api.py` collects all routers under a parent `/api` router with auth dependency.

This pattern was adopted to eliminate `api.py` as a merge bottleneck when multiple agents work in parallel.

### Dependency injection

FastAPI's `Depends()` system is used for config, database, index manager, KB service, and LLM service injection. Module-level singletons with lazy initialization:

- `get_config()` — loads `PyriteConfig` from config file
- `get_db()` — creates `PyriteDB` connection
- `get_index_mgr()` — creates `IndexManager` with db and config
- `get_kb_service()` — creates `KBService` (rebuilds if config/db changed)
- `get_llm_service()` — creates `LLMService` with DB settings override and config fallback

Tests override these globals directly via `api_module._config = ...`.

### LLM Service dependency (`get_llm_service`)

The LLM service reads AI configuration from two layers:
1. **DB settings** (set via Settings page): `ai.provider`, `ai.apiKey`, `ai.model`, `ai.baseUrl`
2. **Config file fallback**: `config.settings.ai_provider`, `ai_api_key`, etc.

The service is cached as a module-level singleton. When any `ai.*` setting is updated via the settings endpoint, `invalidate_llm_service()` is called to reset the cache so the next request rebuilds it with new settings.

### Rate limiting

slowapi with `get_remote_address` key function. Read endpoints: 100/minute. Write endpoints: 30/minute. Health check is not rate-limited (infra probes).

### Authentication and Tier Enforcement

Optional API key via `X-API-Key` header or `api_key` query param. When `config.settings.api_key` is empty, auth is disabled (backwards-compatible).

Role-based access control enforces three tiers (read/write/admin), matching the MCP server's model:
- **Read tier** (default): GET endpoints — search, list, browse
- **Write tier**: POST/PUT/DELETE on entries, starred, settings, AI endpoints (they cost money)
- **Admin tier**: index sync, KB create/delete/gc, git commit/push, plugin management

Key resolution: `api_keys` list in settings with `{key_hash, role, label}` (SHA-256 hashed). Legacy single `api_key` grants admin access. `resolve_api_key_role()` resolves key → role, `requires_tier(tier)` is a FastAPI dependency that enforces minimum tier per endpoint.

### CORS

Configured from `config.settings.cors_origins`. Credentials disabled when wildcard origin is used (spec compliance).

## Endpoint Summary

| Endpoint | Method | Module | Description |
|----------|--------|--------|-------------|
| `/api/kbs` | GET | kbs.py | List knowledge bases |
| `/api/search` | GET | search.py | Full-text search (keyword/semantic/hybrid modes) |
| `/api/entries` | GET | entries.py | Paginated entry listing |
| `/api/entries/titles` | GET | entries.py | Lightweight autocomplete data |
| `/api/entries/resolve` | GET | entries.py | Wikilink target resolution |
| `/api/entries/{id}` | GET/PUT/DELETE | entries.py | Entry CRUD |
| `/api/entries` | POST | entries.py | Create entry |
| `/api/timeline` | GET | timeline.py | Timeline events |
| `/api/tags` | GET | tags.py | Tags with counts |
| `/api/tags/tree` | GET | tags.py | Hierarchical tag tree |
| `/api/stats` | GET | admin.py | Index statistics |
| `/api/index/sync` | POST | admin.py | Trigger incremental sync |
| `/api/ai/status` | GET | admin.py | AI/LLM provider status |
| `/api/ai/summarize` | POST | ai_ep.py | AI summary of an entry |
| `/api/ai/auto-tag` | POST | ai_ep.py | AI tag suggestions |
| `/api/ai/suggest-links` | POST | ai_ep.py | AI wikilink suggestions |
| `/api/ai/chat` | POST | ai_ep.py | RAG chat (SSE streaming) |
| `/api/starred` | GET/POST | starred.py | List/star entries |
| `/api/starred/{id}` | DELETE | starred.py | Unstar entry |
| `/api/starred/reorder` | PUT | starred.py | Reorder starred entries |
| `/api/kbs/{kb}/templates` | GET | templates.py | List templates |
| `/api/kbs/{kb}/templates/{name}` | GET | templates.py | Get template detail |
| `/api/kbs/{kb}/templates/{name}/render` | POST | templates.py | Render template |
| `/api/daily/{date}` | GET | daily.py | Get/create daily note |
| `/api/daily/dates` | GET | daily.py | List dates with daily notes |
| `/api/settings` | GET/PUT | settings_ep.py | Get/bulk-update settings |
| `/api/settings/{key}` | GET/PUT/DELETE | settings_ep.py | Single setting CRUD |
| `/api/versions/{entry_id}` | GET | versions.py | Entry version history |
| `/api/graph` | GET | graph.py | Knowledge graph (nodes + edges) |
| `/api/kbs` | POST | admin.py | Create KB (incl. ephemeral) |
| `/api/kbs/{name}` | DELETE | admin.py | Delete KB |
| `/api/kbs/gc` | POST | admin.py | Garbage-collect ephemeral KBs |
| `/api/plugins` | GET | admin.py | List installed plugins |
| `/api/plugins/{name}` | GET | admin.py | Plugin detail |
| `/api/entries/import` | POST | entries.py | Import entries (file upload) |
| `/api/entries/export` | GET | entries.py | Export entries (JSON/MD/CSV) |
| `/api/entries/resolve-batch` | POST | entries.py | Batch wikilink resolution |
| `/api/entries/wanted` | GET | entries.py | Wanted pages (broken links) |
| `/ws` | WebSocket | websocket.py | Real-time entry/sync events |
| `/api/kbs/{kb}/commit` | POST | git_ops.py | Commit KB changes to git |
| `/api/kbs/{kb}/push` | POST | git_ops.py | Push KB commits to remote |
| `/health` | GET | api.py | Health check (not behind /api) |

## Adding New Endpoints

1. Create a new module in `pyrite/server/endpoints/` with its own `APIRouter`
2. Import request/response models from `../schemas.py` (add new ones there)
3. Import shared deps from `..api` (`get_config`, `get_db`, `get_llm_service`, `limiter`, etc.)
4. Add the router import to `endpoints/__init__.py`'s `all_routers` list
5. Write tests — the test pattern uses `TestClient(app)` with injected globals

## Related

- [ADR-0007](../adrs/0007-ai-integration-architecture.md) — AI integration architecture
- [ADR-0010](../adrs/0010-content-negotiation-and-format-support.md) — Content negotiation
- [LLM Service](llm-service.md) — Provider-agnostic LLM abstraction
- [MCP Server](mcp-server.md) — The other server interface (MCP tools)
- [Storage Layer](storage-layer.md) — PyriteDB that endpoints query
- [Web Frontend](web-frontend.md) — SvelteKit frontend consuming this API
