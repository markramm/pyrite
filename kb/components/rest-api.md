---
id: rest-api
type: component
title: "REST API Server"
kind: service
path: "pyrite/server/"
owner: "markr"
dependencies: ["fastapi", "slowapi", "pydantic", "pyrite.storage", "pyrite.config", "pyrite.services"]
tags: [core, api, server, fastapi]
---

FastAPI HTTP + WebSocket server structured as a factory (`create_app()`) with fully isolated app instances. All service state lives on `app.state` with DI providers wired via `dependency_overrides` for test isolation. Three-tier access model (read/write/admin) resolved from API keys, session cookies, or anonymous tier.

## Architecture

- Factory pattern: `create_app()` in `api.py` creates isolated FastAPI instances
- 17 endpoint modules under `endpoints/`, each an `APIRouter` under `/api` prefix
- Auth endpoints mounted outside `/api` for OAuth login/logout/callback
- Rate limiting via `slowapi` with SHA-256-anonymized client IPs
- WebSocket at `/ws` for real-time index progress and multi-tab updates

## Key Modules

- `api.py` — app factory, DI providers, auth middleware, CORS, rate limiter
- `endpoints/` — 17 domain routers (entries, search, kbs, collections, graph, timeline, AI, etc.)
- `auth_endpoints.py` — OAuth routes outside /api prefix
- `schemas.py` — Pydantic request/response models
- `mcp_server.py` — Model Context Protocol server for AI agents
- `websocket.py` — WebSocket connection manager
- `static.py` — SPA static file serving

## Related

- [[server-schemas]] — Pydantic models
- [[mcp-server]] — MCP surface
- [[mcp-tool-schemas]] — tool definitions
