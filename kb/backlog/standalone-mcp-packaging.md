---
type: backlog_item
title: "Standalone MCP Server Packaging"
kind: feature
status: proposed
priority: critical
effort: M
tags: [distribution, mcp, packaging, go-to-market]
---

# Standalone MCP Server Packaging

Package the Pyrite MCP server as a standalone installable (`pip install pyrite-mcp`) so AI agent users can get a working MCP knowledge server in under 60 seconds without installing the full Pyrite CLI, web server, or extensions.

## Motivation

This is the #1 go-to-market blocker for the agent shared memory market. Today, using Pyrite as an MCP server requires cloning the repo, installing all dependencies, and configuring a KB. The target experience is:

```bash
pip install pyrite-mcp
pyrite-mcp init my-research    # creates KB + config
pyrite-mcp serve --tier write  # starts MCP server
```

## Scope

- Extract `pyrite-mcp` as a minimal PyPI package containing:
  - MCP server (`mcp_server.py`)
  - Storage layer (database, repository, index)
  - Services (kb_service, search_service)
  - Schema and models
  - Format serializers
- Exclude: web server, CLI beyond `init`/`serve`, extensions, LLM service
- Single `pyrite-mcp init` command that creates a KB directory with `kb.yaml`
- `pyrite-mcp serve --tier read|write|admin` for stdio MCP transport
- Publish to PyPI
- Add to MCP community registry

## Acceptance Criteria

- [ ] `pip install pyrite-mcp` works in a clean virtualenv
- [ ] `pyrite-mcp init <name>` creates a working KB
- [ ] `pyrite-mcp serve --tier write` starts an MCP server over stdio
- [ ] All MCP tools, prompts, and resources work
- [ ] Package size is minimal (no web frontend, no optional AI deps)
- [ ] README with 3-minute quickstart for Claude Desktop / Claude Code

## References

- Agent shared memory positioning: `kb/positioning/agent-shared-memory.md`
