---
id: epic-web-ui-orchestration-multi-agent-research-workflows-in-the-browser
title: 'Epic: Web UI Orchestration -- Multi-Agent Research Workflows in the Browser'
type: backlog_item
tags:
- epic
- web
- orchestration
- agents
- journalism
links:
- target: epic-journalists-pyrite-wiki-hosted-research-platform-for-independent-journalists
  relation: subtask_of
  kb: pyrite
importance: 5
---

## Problem

Pyrite has rich MCP tools and a task plugin but no way to run multi-agent workflows from within the web UI. Research workflows currently require Claude Code as the orchestrator. A journalist using the web UI cannot launch agent-assisted investigation workflows -- they can only use single-turn AI chat.

## Solution

Add an orchestration layer to the Pyrite backend that runs multi-agent workflows (powered by open-multi-agent or similar), streams progress to the UI, and writes results directly into KB entries.

### Components

1. **Backend orchestration endpoint** -- POST /api/orchestrate accepts a goal + agent config, spins up an orchestrator with MCP tools pointing back at Pyrite, streams progress events via SSE
2. **Orchestration panel in UI** -- goal input, agent roster display, live task DAG visualization (reuse Cytoscape graph component), progress stream, token usage tracking
3. **Workflow templates** -- reusable research patterns (Deep Research, KB Audit, Cross-KB Investigation, Seed and Extend) that define agent roles, tool access tiers, and output schemas
4. **Result integration** -- agent outputs become KB entries automatically, linked to the workflow that produced them

### Key Design Decisions

- Backend orchestrates, not the browser (keeps API keys server-side, enables long-running workflows)
- Pyrite is both the orchestrator MCP server AND the result destination
- BYOK API keys (user provides their own LLM keys)
- Kanban board becomes the agent work queue (ADR-0019 pull-based model)

## Success Criteria

- A journalist can type a research goal in the UI and watch agents execute
- Results appear as KB entries with source chains
- Workflow can be stopped/approved at checkpoints (human-in-the-loop)
- At least 3 workflow templates available
