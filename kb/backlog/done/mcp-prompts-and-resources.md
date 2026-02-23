---
type: backlog_item
title: "MCP Prompts and Resources"
kind: feature
status: done
priority: high
effort: M
tags: [ai, mcp, api]
---

Extend the MCP server (ADR-0006, ADR-0007) with prompts and resources:

**MCP Prompts** — Pre-built prompt templates offered to MCP clients:
- `research_topic` — "Research {topic} across all KBs" → searches, summarizes findings
- `summarize_entry` — "Summarize entry {id}" → generates summary
- `find_connections` — "Find connections between {entry_a} and {entry_b}" → graph traversal + analysis
- `daily_briefing` — "Generate briefing from recent entries" → aggregates recent activity

**MCP Resources** — Expose KB content as browsable resources:
- `pyrite://kbs` — list of knowledge bases with metadata
- `pyrite://kbs/{name}/entries` — paginated entry listing
- `pyrite://entries/{id}` — full entry content with metadata, backlinks, tags

**Implementation:**
- Add `list_prompts()`, `get_prompt()` handlers to `PyriteMCPServer`
- Add `list_resources()`, `read_resource()` handlers
- Prompts that use LLM require `LLMService` (degrade gracefully if no key)
- Resources are read-only, available at all tiers

This makes Pyrite a first-class knowledge source for Claude Desktop, Cline, Windsurf, and any MCP client.
