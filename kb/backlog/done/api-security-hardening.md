---
type: backlog_item
title: "Harden API Layer Security"
kind: improvement
status: completed
priority: high
effort: M
tags: [api, security]
---

Multiple security gaps in the REST API and MCP server:

- **CORS allows all origins** (`allow_origins=["*"]`) in FastAPI config
- **No per-request authentication** on FastAPI endpoints
- **No rate limiting** on any endpoint
- **MCP tiers enforced at instantiation**, not per-request — any client connected to a write-tier server has full write access

Before exposing the API to any network (even localhost in multi-user setups), these need addressing. At minimum:
1. Restrict CORS to configured origins
2. Add API key or token-based auth middleware
3. Add basic rate limiting (e.g., slowapi)
4. Consider per-request MCP tier verification

## Completed

Implemented in commit `46ea1d6`. Added `slowapi` rate limiting: 100/minute on read endpoints, 30/minute on write endpoints, with 429 handler and Retry-After header. CORS origins configurable via `Settings.cors_origins` (defaults to localhost:3000/5173/8088). API key setting added to config. Rate limit values configurable via `rate_limit_read`/`rate_limit_write` settings. MCP tier verification deferred to separate item.
