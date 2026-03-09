---
id: standard-type-split
title: "Split standard type into programmatic_validation and development_convention"
type: backlog_item
tags:
- workflow
- agents
- software
- wave-2
- extension:software-kb
links:
- target: adr-0019
  relation: implements
  note: "Ontological split from the kanban ADR"
- target: software-project-plugin
  relation: part_of
kind: feature
status: done
priority: high
effort: M
---

# Split standard type into programmatic_validation and development_convention

## Problem

The current `standard` type conflates two fundamentally different things: verifiable specifications (linting rules, test patterns, commit formats) and judgment-based guidance (design preferences, naming conventions). Agents need to know which standards are automated gates vs which require human review judgment.

## Solution

Replace `standard` with two entry types per ADR-0019:

- **`programmatic_validation`** — Has a programmatic check. Fields: check_command, enforced (bool), pass_criteria. The system can evaluate compliance as pass/fail. Maps to existing standards with `enforced: true`.
- **`development_convention`** — Judgment-based guidance. Fields: category, examples. Carried as context for agents; compliance evaluated by human reviewers. Maps to existing standards with `enforced: false`.

### Migration

- Existing standards with `enforced: true` → `programmatic_validation`
- Existing standards with `enforced: false` → `development_convention`
- Retain `standard` as a deprecated alias during transition

## Acceptance Criteria

- Both types registered in software-kb plugin with validators
- `pyrite sw validations` and `pyrite sw conventions` CLI commands
- Migration script converts existing `standard` entries
- `sw_validate` MCP tool runs all relevant `programmatic_validation` checks
- Agent schema surfaces the distinction clearly
