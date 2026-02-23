---
type: adr
title: "MCP Three-Tier Tool Model"
adr_number: 6
status: accepted
deciders: ["markr"]
date: "2025-08-01"
tags: [architecture, mcp, ai-agents]
---

## Context

AI agents connecting via MCP need different permission levels. A research agent should search but not delete. A drafting agent should create but not manage KBs.

## Decision

Three tiers of MCP tools:
- **Read**: list, search, get, timeline, backlinks, tags, stats, schema
- **Write**: create, update, delete (plus all read tools)
- **Admin**: index sync, KB manage (plus all write tools)

Plugins register tools at specific tiers. The server is started at a chosen tier.

## Consequences

- Safe to give read-tier access to any agent
- Plugin MCP tools merge into the same tier system
- Currently 4 software-kb read tools + 2 write tools registered via plugin
- Server defaults to write tier for Claude Code integration
