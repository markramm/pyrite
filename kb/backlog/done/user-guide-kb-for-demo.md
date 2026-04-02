---
id: user-guide-kb-for-demo
title: "User guide KB and demo site landing experience"
type: backlog_item
tags: [onboarding, demo, documentation, mcp]
kind: feature
status: done
priority: high
effort: M
---

## Problem

The demo site at demo.pyrite.wiki drops visitors into an entries list with no explanation of what Pyrite is, how to use it, or how to connect via MCP. There's no user guide, no getting started content, and no MCP connection instructions visible in the UI.

## Solution

Create a `pyrite-guide` KB containing user-facing documentation as Pyrite entries. Set it as the default KB on the demo site. Combined with the KB orientation page ([[web-ui-kb-orientation-page]]), the guide's orient page becomes the effective demo homepage.

### Guide KB entries

- **What is Pyrite** — overview, value proposition, key concepts (note)
- **Getting Started** — install, init, create entries, search (note)
- **Connecting via MCP** — Claude Desktop, Claude Code, OpenAI, Gemini config JSON with copy buttons (note)
- **Understanding Entry Types** — what types are, how schemas work, built-in vs plugin types (note)
- **Search Modes** — keyword, semantic, hybrid explained with examples (note)
- **Knowledge Graph** — what the graph shows, how links work, wikilink syntax (note)
- **Plugins and Extensions** — what plugins add, how to install, available plugins (note)
- **Self-Hosting** — Docker setup, VPS deployment, security considerations (note)
- **For Developers** — CLI reference, REST API, MCP tools, plugin protocol (note)

### Demo site configuration

- The guide KB is registered first (before other KBs) so it's the default selection
- The orient page for the guide KB serves as the landing page
- MCP connection instructions include the demo server's MCP endpoint if applicable, plus local install instructions

### MCP instructions content

Show config JSON for:
1. Claude Desktop / Claude Code (local `pyrite mcp`)
2. OpenAI Codex CLI
3. Gemini CLI
4. Generic MCP client

Each with a copy-to-clipboard button and a brief explanation of what happens when connected.

## Dependencies

- [[web-ui-kb-orientation-page]] — the orient page renders the guide KB as the landing experience

## Success criteria

- New visitor to demo.pyrite.wiki sees "What is Pyrite" content immediately
- MCP connection instructions are findable within 2 clicks
- Guide entries are well-written, concise, and link to each other
- The guide KB works as a standalone KB that ships with Pyrite (not just for the demo)
