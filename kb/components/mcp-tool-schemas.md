---
id: mcp-tool-schemas
title: MCP Tool Schemas
type: component
kind: module
path: pyrite/server/tool_schemas.py
owner: core
dependencies: []
tags:
- core
- mcp
---

Pure-data module that externalizes MCP tool metadata (descriptions and JSON Schema input shapes) from the handler dispatch logic. Contains three dicts — `READ_TOOLS`, `WRITE_TOOLS`, and `ADMIN_TOOLS` — that the MCP server advertises to clients during capability negotiation.

## Key Methods / Classes

- `READ_TOOLS` — read-only tool schemas: `kb_list`, `kb_search`, `kb_get`, and related query tools
- `WRITE_TOOLS` — mutation tool schemas: `kb_create` and related write operations
- `ADMIN_TOOLS` — administrative tool schemas: `kb_index_sync`, `kb_manage`, and related ops

## Consumers

- `mcp_server.py` — imports all three dicts for tool registration and capability advertisement

## Related

- [[mcp-server]] — MCP server that uses these schemas for dispatch
- [[pyrite-plugin-protocol]] — plugin protocol that extends the tool surface
