---
id: ji-cli-subcommands-for-investigation-queries
title: 'JI: CLI subcommands for investigation queries'
type: backlog_item
tags:
- ji
- cli
- ux
kind: feature
priority: high
effort: M
---

## Problem

The journalism-investigation plugin has 11 MCP tools but no CLI commands. AI agents can query via MCP; humans have no `pyrite investigation` subcommands and must use raw `pyrite search` or `pyrite get`.

## Scope

Add a Typer sub-app registered via the plugin get_cli_commands() method. Commands should mirror the read-tier MCP tools:

- `pyrite investigation timeline [--from DATE] [--to DATE] [--actor NAME] [--type TYPE] [--min-importance N] -k KB`
- `pyrite investigation entities [--type TYPE] [--jurisdiction J] [--min-importance N] -k KB`
- `pyrite investigation sources [--reliability R] [--classification C] -k KB`
- `pyrite investigation claims [--status S] [--confidence C] -k KB`
- `pyrite investigation evidence-chain CLAIM_ID -k KB`
- `pyrite investigation network ENTRY_ID -k KB`

Output should be human-readable tables (rich or tabulate), with --json flag for machine output.

## Acceptance Criteria

- All 6 commands work and produce formatted output
- --json flag outputs raw JSON on all commands
- Commands share the same filter logic as MCP handlers (no duplication -- extract shared query functions)
- `pyrite investigation --help` shows all subcommands
