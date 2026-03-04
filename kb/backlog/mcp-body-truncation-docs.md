---
id: mcp-body-truncation-docs
type: backlog_item
title: "Document body truncation behavior in MCP tool schemas"
kind: improvement
status: done
milestone: "0.17"
priority: low
effort: XS
tags: [mcp, documentation, agent-dx]
links:
- mcp-server
- mcp-large-result-handling
---

# Document body truncation behavior in MCP tool schemas

## Problem

Large entry bodies are truncated to ~8K characters in MCP responses. Agents must use `body_offset` to paginate through the rest, but this behavior isn't documented in the MCP tool schema descriptions. Agents discover it only when they notice truncated content.

## Solution

1. Add truncation notice to `kb_get` and `kb_search` tool descriptions in `tool_schemas.py`
2. Include `body_truncated: true` and `body_total_length: N` fields in truncated responses
3. Document the `body_offset` pagination pattern in the tool schema's `description` field

## Files

- `pyrite/server/tool_schemas.py` — tool descriptions
- `pyrite/server/mcp_server.py` — truncation response fields
