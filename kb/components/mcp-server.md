---
type: component
title: "MCP Server"
kind: service
path: "pyrite/server/mcp_server.py"
owner: "markr"
dependencies: ["pyrite.plugins", "pyrite.storage", "pyrite.config"]
tags: [core, mcp, ai-agents]
---

The MCP (Model Context Protocol) server exposes pyrite tools to AI agents like Claude Code over stdio. Implemented as `PyriteMCPServer`, it uses the official `mcp` SDK to serve tools, prompts, and resources.

## Three-Tier Tool Model

Each server instance runs at a single tier, which determines which tools are available:

| Tier | Access Level | Tools |
|------|-------------|-------|
| **read** | Safe for any agent | kb_list, kb_search, kb_get, kb_timeline, kb_backlinks, kb_tags, kb_stats, kb_schema |
| **write** | Trusted agents | read + kb_create, kb_update, kb_delete |
| **admin** | Full control | write + kb_index_sync, kb_manage, kb_commit, kb_push |

Tier is set at construction time via the `tier` parameter and validated against `VALID_TIERS`. Invalid tiers raise `ConfigError`.

## Plugin Tool Merging

After core tools are registered, `_register_plugin_tools()` calls `registry.get_all_mcp_tools(self.tier)` to collect plugin-provided tools. Plugin tools are merged into the same `self.tools` dict, making them indistinguishable from core tools to MCP clients. Plugins register tools via the `get_mcp_tools(tier)` protocol method. Plugin loading failures are silently caught to avoid breaking the server.

Plugins receive a `PluginContext` with shared `config` and `db` references so they don't need to bootstrap their own connections.

## Prompts

Four built-in prompts available at all tiers:

- `research_topic` — search across all KBs, summarize findings, identify gaps
- `summarize_entry` — fetch entry and generate concise summary
- `find_connections` — analyze relationships between two entries
- `daily_briefing` — summarize recent timeline events (configurable lookback days)

Each prompt returns MCP `PromptMessage` objects with pre-built user messages.

## Resources

Static resources and URI templates for browsing:

- `pyrite://kbs` — list all knowledge bases
- `pyrite://kbs/{name}/entries` — list entries in a KB (limit 200)
- `pyrite://entries/{id}` — get a specific entry

Resources are read via `_read_resource()` which dispatches based on URI prefix matching.

## SDK Integration

`build_sdk_server()` creates an `mcp.server.Server` instance and registers async handlers for all MCP protocol methods (list_tools, call_tool, list_prompts, get_prompt, list_resources, list_resource_templates, read_resource). The server runs over stdio via `anyio` in `run_stdio()`.

## Configuration and Startup

- CLI: `pyrite mcp --tier write` or `pyrite-admin mcp`
- Entry point: `main()` in `mcp_server.py` parses `--tier` flag
- Default tier: `read`
- The server creates its own `PyriteDB` and `KBService` instances
- `close()` must be called to release the DB connection

## Consumers

- Claude Code via `.claude-plugin/plugin.json` MCP server config
- Claude Desktop / Cline via manual MCP server setup
- Any MCP-compatible client over stdio

## Related

- [[rest-api]] — HTTP equivalent of MCP tools
- [[kb-service]] — business logic layer used by all tool handlers
- [[pyrite-db]] — database access
- [[schema-validation]] — `kb_schema` tool uses `KBSchema.to_agent_schema()`
