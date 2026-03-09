---
id: bulk-link-creation-command-pyrite-link-bulk-create
title: Bulk link creation command (pyrite link bulk-create)
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
status: accepted
effort: S
---

## Problem

Cross-KB linking produces dozens of links at once. Currently requires looping `pyrite link` N times, each with its own index write. Slow and wasteful.

## Proposed Solution

Add `pyrite link bulk-create` for batch link creation:

\`\`\`
pyrite link bulk-create --file links.yaml --kb <name> [--dry-run]
\`\`\`

### File format

\`\`\`yaml
- source: ooda-loop
  target: pdca-cycle
  target_kb: deming
  relation: parallel_concept
  note: "Both are iterative learning cycles"
\`\`\`

### Also accept stdin

So subagents can pipe output directly without temp files.

## Impacted Files

- `pyrite/cli/link_commands.py` — add `bulk-create` subcommand
- `pyrite/services/link_service.py` or equivalent — batch write logic
- Pattern: similar to existing `kb_bulk_create` MCP tool

## Acceptance Criteria

- Accepts YAML file or stdin with link definitions
- Single index sync after all links created
- `--dry-run` shows what would be created
- Reports created/skipped/failed counts
