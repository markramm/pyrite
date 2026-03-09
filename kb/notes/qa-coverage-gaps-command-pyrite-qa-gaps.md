---
id: qa-coverage-gaps-command-pyrite-qa-gaps
title: QA coverage gaps command (pyrite qa gaps)
type: backlog_item
tags:
- cli
- qa
- agent
links:
- target: epic-agent-cli-feature-requests-for-kb-workflows
  relation: subtask_of
  kb: pyrite
kind: feature
status: review
assignee: agent-b
effort: M
---

## Problem

When populating a KB, there's no structured way to identify coverage gaps relative to the KB's declared scope. Currently requires listing all entries as JSON and manually reasoning about what kb.yaml says should exist vs what actually does.

## Proposed Solution

Add `pyrite qa gaps` command that reports structural coverage gaps (no LLM needed).

### Reports to generate

- Entry types defined in kb.yaml with 0 entries
- Entry types with fewer than N entries (configurable threshold)
- Tags referenced in kb.yaml guidelines/goals that appear on 0 entries
- Entries with no outbound links (orphans)
- Entries with no inbound links (unreferenced)
- Distribution: entries per type, per tag (top N), per importance band

### Output

Structured (JSON/YAML) so subagents can consume it for research planning.

## Impacted Files

- `pyrite/services/qa_service.py` — add gap analysis logic
- `pyrite/cli/qa_commands.py` — add `gaps` subcommand
- Uses existing index queries and kb.yaml parsing (intent layer)

## Acceptance Criteria

- Reports all gap categories listed above
- JSON output mode for agent consumption
- Configurable thresholds for "too few entries"
- No LLM dependency — pure structural analysis
