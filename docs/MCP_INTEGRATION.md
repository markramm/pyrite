
# MCP Integration Guide

This project exposes **tools** via the Model Context Protocol (MCP) for AI agent integration.
The MCP server implementation is in `pyrite/server/mcp_server.py`.

## Setup

See [MCP_SETUP.md](MCP_SETUP.md) for detailed setup instructions.

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `kb_list` | List all mounted knowledge bases |
| `kb_search` | Full-text search across KBs with filters |
| `kb_get` | Get entry by ID |
| `kb_create` | Create new entry (event, actor, etc.) |
| `kb_update` | Update existing entry |
| `kb_timeline` | Get timeline events by date range |
| `kb_tags` | Get all tags with counts |
| `kb_actors` | Get all actors mentioned in events |
| `kb_index_sync` | Sync the search index with KB files |

## Transport

The MCP server uses stdio transport for direct integration with AI tools like Claude Code.

Please refer to the MCP server registry contribution guide for metadata, security, and deployment requirements.
