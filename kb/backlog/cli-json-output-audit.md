---
id: cli-json-output-audit
title: "CLI --format json Audit and Consistency"
type: backlog_item
tags:
- improvement
- cli
- agent-infrastructure
kind: improvement
priority: high
effort: M
status: done
---

## Problem

Autonomous agents (OpenClaw, Claude Code, Codex) use the CLI as their primary interface. The `--format json` flag exists on many commands, but there is no guarantee that every subcommand supports it, that the JSON envelope is consistent across commands, or that the output is free of ANSI escape codes and rich-formatting artifacts when `--format json` is specified.

An agent parsing `pyrite search "topic" --format json` needs clean, predictable JSON. If any command falls back to rich-formatted text, the agent's workflow breaks silently.

## Proposed Solution

1. **Audit every CLI subcommand** for `--format json` support. Document which commands have it and which don't.
2. **Add `--format json` to all commands that produce output.** This includes `qa`, `sw`, `collections`, `index health`, and any other subcommands.
3. **Standardize the JSON envelope.** Every command should return:
   ```json
   {
     "status": "ok",
     "count": 5,
     "results": [...],
     "has_more": false
   }
   ```
   Error responses should return:
   ```json
   {
     "status": "error",
     "error": "Entry not found",
     "code": "ENTRY_NOT_FOUND"
   }
   ```
4. **Suppress rich formatting** when `--format json` or `--format yaml` is active. No ANSI escape codes, no table borders, no progress spinners in stdout.
5. **Add integration tests** verifying that `--format json` output is valid JSON for every command.

## Why This Matters for Agent-as-User

This is the single biggest friction reducer for CLI-based agent integration. Every other improvement depends on agents being able to reliably parse CLI output.

## Related

- [[bhag-self-configuring-knowledge-infrastructure]] — Agents use CLI as primary interface
- [[content-negotiation-and-formats]] — REST API already handles this well; CLI needs parity
