---
id: qa-auto-fix-command-pyrite-qa-fix
title: QA auto-fix command (pyrite qa fix)
type: backlog_item
tags:
- cli
- qa
- agent
kind: feature
priority: high
effort: M
links:
- target: epic-agent-cli-feature-requests-for-kb-workflows
  relation: subtask_of
  kb: pyrite
---

## Problem

The validate→fix loop for KB QA requires parsing validation output, determining fixes, and running individual `pyrite update` commands per issue. For a 50-entry KB this means 50+ manual commands for issues with obvious mechanical fixes.

## Proposed Solution

Add `pyrite qa fix` command that auto-fixes safe structural issues found by `pyrite qa validate`.

### Safe fixes to handle

- Normalize date formats to YYYY-MM-DD (e.g., `'2006'` → `'2006-01-01'`)
- Add missing required fields with type-appropriate defaults (e.g., `importance: 5`)
- Fix broken wikilinks to closest match by edit distance
- Normalize tag casing

### Required flags

- `--dry-run` — show what would change without writing (must have)
- `--fix-rule <rule>` — target only specific issue types (nice to have)

## Impacted Files

- `pyrite/services/qa_service.py` — add fix resolution logic per checker
- `pyrite/cli/qa_commands.py` — add `fix` subcommand
- Existing validation checkers — add `fix()` method or resolution callback

## Acceptance Criteria

- `pyrite qa fix --dry-run` shows planned fixes without writing
- `pyrite qa fix` applies safe structural fixes and reports changes
- Broken wikilinks fixed to closest edit-distance match
- Date normalization, tag casing, missing field defaults all handled
- Unsafe/ambiguous issues left for manual resolution with clear messaging
