---
id: authenticated-mcp-endpoint-for-remote-access
title: Authenticated MCP Endpoint for Remote Access
type: backlog_item
tags:
- mcp
- security
- hosting
- authentication
links:
- target: epic-journalists-pyrite-wiki-hosted-research-platform-for-independent-journalists
  relation: subtask_of
  kb: pyrite
importance: 5
---

## Problem

Pyrite MCP server currently runs locally via stdio transport. For the hosted journalists.pyrite.wiki service, external users need to connect to Pyrite MCP over the network from their Claude Code or Google CLI installations with proper authentication and access control.

## Solution

Expose an authenticated MCP endpoint over HTTPS (SSE transport) that:
1. Accepts token-based authentication (Bearer token in headers)
2. Maps the authenticated user to their Pyrite user account and permissions
3. Enforces three-tier access control (read/write/admin) per the existing permission model
4. Supports the full MCP tool surface including software-kb and journalism-investigation tools

### User Experience

A Claude Code user adds to their MCP config:
```json
{
  "mcpServers": {
    "cascade": {
      "url": "https://journalists.pyrite.wiki/mcp",
      "headers": { "Authorization": "Bearer <their-token>" }
    }
  }
}
```

Now every Claude Code session has access to the pre-populated research KBs through standard MCP tools with three-tier access control.

## Prerequisites

- Multi-user auth system (already built)
- MCP server (already built, needs SSE/HTTP transport)
- TLS/reverse proxy setup for the hosted instance

## Success Criteria

- External MCP client can connect, authenticate, and list tools
- Per-user KB permissions are enforced on every tool call
- Connection is secure (HTTPS + token auth)
- Works with Claude Code and any MCP-compatible client
