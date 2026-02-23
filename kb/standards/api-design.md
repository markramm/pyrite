---
type: standard
title: "API & MCP Tool Design"
category: api
enforced: false
tags: [api, mcp]
---

## MCP Tool Naming
- Plugin tools prefixed with short name: `sw_`, `zettel_`, `wiki_`
- Read tools: list/query operations
- Write tools: create/update operations
- Admin tools: management operations

## Tool Schema
Every MCP tool must have:
- `description` — clear, actionable description
- `inputSchema` — JSON Schema with type, properties, required
- `handler` — method reference on the plugin class

## Error Handling
- Return `{"error": "message"}` for user errors
- Return guidance for file creation (create tools don't write files directly, they return instructions)
