---
id: mcp-rate-limiting
title: "MCP Server Rate Limiting"
type: backlog_item
tags:
- feature
- mcp
- security
- demo-site
kind: feature
priority: high
effort: S
status: planned
links:
- demo-site-deployment
- api-security-hardening
- roadmap
---

## Problem

The REST API has slowapi rate limiting (#4, done). The MCP server has no rate limiting. An agent in a tight loop — or a malicious actor on the demo site — could hammer the server with unlimited requests. This blocks the demo site and any public-facing deployment.

## Solution

Add rate limiting to MCP tool handlers, reusing the tier-based approach from the REST API.

### Configuration

```yaml
# pyrite.yaml
mcp:
  rate_limits:
    read: 100/minute    # search, get, list operations
    write: 30/minute    # create, update, bulk_create
    admin: 10/minute    # kb_manage, kb_commit, kb_push
```

### Implementation

- Per-client rate tracking (by API key or connection ID)
- Rate limit headers in MCP responses
- Graceful error when limit exceeded (retry-after hint)
- Exempt local connections (stdio transport) by default — rate limits only apply to SSE/HTTP transport

### Demo Site Specifics

- Anonymous connections get read-tier limits
- Authenticated connections get write-tier limits
- Admin operations disabled for anonymous

## Prerequisites

- REST API rate limiting patterns (done, #4)
- MCP tier enforcement (done, integrated into tool handlers)

## Success Criteria

- MCP tools rate-limited per tier
- Demo site can handle concurrent visitors without degradation
- Local development unaffected (stdio exempt)
- Rate limit errors include retry-after timing

## Launch Context

Blocker for demo site. Small effort — patterns already exist in the REST API layer. Just needs to be applied to MCP tool handlers.
