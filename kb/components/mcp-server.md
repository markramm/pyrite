---
type: component
title: "MCP Server"
kind: service
path: "pyrite/server/mcp_server.py"
owner: "markr"
dependencies: ["pyrite.plugins", "pyrite.storage", "pyrite.config"]
tags: [core, mcp, ai-agents]
---

The MCP (Model Context Protocol) server exposes pyrite tools to AI agents like Claude Code over stdio.

## Features
- Three-tier tool model (read/write/admin)
- Core tools: kb_list, kb_search, kb_get, kb_create, kb_update, kb_delete, kb_timeline, kb_backlinks, kb_tags, kb_stats, kb_schema
- Plugin tools merged per tier (e.g., sw_adrs, sw_standards from software-kb)
- Runs over stdio for Claude Code integration

## Configuration
Started via `pyrite-admin mcp` or `pyrite mcp` at write tier by default.
