---
id: cli-link-suggest-command-pyrite-link-suggest
title: CLI link suggest command (pyrite link suggest)
type: backlog_item
tags:
- cli
- links
- agent
links:
- target: epic-agent-cli-feature-requests-for-kb-workflows
  relation: subtask_of
  kb: pyrite
kind: feature
status: done
priority: low
assignee: agent-e
effort: M
---

## Problem

The `/api/ai/suggest-links` REST endpoint exists but isn't accessible from CLI. Subagents can't easily call the API (need server URL/port, HTTP calls). CLI is the natural interface for agent workflows.

## Proposed Solution

Expose link suggestion as a CLI command:

\`\`\`
pyrite link suggest <entry-id> --kb <name> [--target-kb <name>] [--limit 10] [--format json]
\`\`\`

### Behavior

Given an entry, find entries in the same or another KB that are likely related (by title, tags, summary overlap via FTS5). Return ranked candidates with relevance indicator.

### Modes

- FTS5-only mode for bulk operations (cheap, fast)
- LLM mode for high-value entries (if existing API endpoint uses LLM)

## Impacted Files

- `pyrite/cli/link_commands.py` — add `suggest` subcommand
- `pyrite/server/endpoints/ai_ep.py` — existing API logic to reuse
- May need to extract shared logic into a service

## Acceptance Criteria

- CLI command wraps existing API suggest-links logic
- FTS5-only mode available for bulk use
- JSON output for agent consumption
- Cross-KB suggestion supported via `--target-kb`
