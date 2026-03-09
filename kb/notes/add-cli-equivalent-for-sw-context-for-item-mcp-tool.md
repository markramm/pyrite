---
id: add-cli-equivalent-for-sw-context-for-item-mcp-tool
title: Add CLI equivalent for sw_context_for_item MCP tool
type: backlog_item
tags:
- cli
- software-kb
- agent
kind: bug
status: in_progress
priority: high
assignee: agent-f
effort: S
---

## Problem

sw_context_for_item is one of the most important MCP tools in the software-kb workflow — it assembles the full context bundle for a backlog item (linked ADRs, components, validations, conventions, reviews, work logs, dependencies). However it has no CLI equivalent.

The software-kb skill documents it in the CLI equivalents section but pyrite sw context-for-item does not exist. This was discovered when coding agents tried to use it during a parallel work session and got exit code 2.

Agents fall back to pyrite get + pyrite search which gives only partial context and misses linked validations, review history, and dependency status.

## Impacted Files

- extensions/software-kb/src/pyrite_software_kb/cli.py — add context-for-item subcommand
- The MCP tool implementation already exists in the plugin and can be reused

## Acceptance Criteria

- pyrite sw context-for-item <item-id> --kb <name> works from CLI
- Output matches the MCP tool output (item details, linked ADRs, components, validations, reviews, work logs, dependency status)
- JSON output mode for agent consumption
- Human-readable rich output as default
