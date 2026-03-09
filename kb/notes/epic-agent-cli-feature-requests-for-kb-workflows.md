---
id: epic-agent-cli-feature-requests-for-kb-workflows
title: 'Epic: Agent CLI feature requests for KB workflows'
type: backlog_item
tags:
- cli
- agent
- demo-site
- epic
links:
- target: qa-auto-fix-command-pyrite-qa-fix
  relation: has_subtask
  kb: pyrite
- target: qa-coverage-gaps-command-pyrite-qa-gaps
  relation: has_subtask
  kb: pyrite
- target: cli-link-suggest-command-pyrite-link-suggest
  relation: has_subtask
  kb: pyrite
- target: bulk-link-creation-command-pyrite-link-bulk-create
  relation: has_subtask
  kb: pyrite
- target: init-templates-for-intellectual-biography-and-movement-kb-types
  relation: has_subtask
  kb: pyrite
kind: epic
status: review
priority: high
assignee: claude
effort: XL
---

## Overview

Feature requests from an agent-driven KB workflow operator (Claude Code orchestrating subagents via CLI). These unblock demo site KB preparation by eliminating manual repetitive work in the validate→fix loop, enabling systematic gap analysis, and reducing boilerplate for new KB creation.

## Context

The requesting workflow uses pyrite entirely through CLI (no MCP) across multiple KBs (Boyd, Wardley, Blank, etc.) with 5 core workflows: KB creation, population, QA validation, gap research, and cross-KB linking.

## Source

From `/Users/markr/tcp-kb-internal/agent-cli-feature-requests.md` (2026-03-08).

## Acceptance Criteria

- All 5 subtask features implemented and tested
- Agent CLI workflows can operate without manual workarounds
- Demo site KBs can be built and validated efficiently
