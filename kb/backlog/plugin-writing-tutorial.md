---
id: plugin-writing-tutorial
title: "Plugin Writing with Claude Code Tutorial"
type: backlog_item
tags:
- docs
- tutorial
- plugins
- claude-code
- launch
kind: feature
priority: high
effort: S
status: planned
links:
- extension-builder-skill
- plugin-repo-extraction
- roadmap
---

## Problem

Pyrite's plugin system is powerful (16-method protocol, entry types, MCP tools, validators, hooks, migrations) but there's no tutorial showing how to build one. The `extension-builder` skill can scaffold a plugin end-to-end via Claude Code, but nobody knows about it.

## Solution

A step-by-step tutorial: "Build a Pyrite Plugin with Claude Code." Walk through creating a real plugin from scratch using the `extension-builder` skill and Claude Code's agent capabilities.

### Content Outline

1. **What you'll build** — a small but complete plugin (e.g., a "bookmarks" or "reading-list" plugin with custom entry type, validator, and MCP tool)
2. **Prerequisites** — Pyrite installed, Claude Code configured with Pyrite MCP
3. **Scaffold the plugin** — use the `extension-builder` skill to generate the structure
4. **Customize entry types** — add fields, validation rules, AI instructions
5. **Add an MCP tool** — expose plugin functionality to agents
6. **Test it** — run the generated test suite, add a test
7. **Install and use** — `pip install -e .`, create entries, search
8. **Publish** — package for PyPI (if desired)

### Format

Markdown document in the repo (e.g., `docs/tutorials/plugin-writing.md`) or a KB entry. Should be linkable from README and the awesome plugins page.

### Key Selling Point

This tutorial demonstrates the BHAG in miniature: an agent (Claude Code) builds a Pyrite extension, tests it, installs it, and starts using it. The human's role is steering, not typing. That's the pitch.

## Prerequisites

- Plugin repo extraction (#107) — so the tutorial shows the standalone pattern
- Getting Started tutorial — so readers already have Pyrite running

## Success Criteria

- Tutorial published and linked from README
- A user can follow the tutorial and have a working plugin in < 30 minutes
- Tutorial exercises the `extension-builder` skill end-to-end
- Resulting plugin is installable via `pip install -e .`
