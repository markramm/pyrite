---
id: masfactory-integration-as-pyrite-orchestration-layer
title: MASFactory integration as Pyrite orchestration layer
type: backlog_item
tags:
- integration
- agent-infrastructure
- workflows
- masfactory
- spike
links:
- target: native-workflow-patterns-loops-checkpoints-parallel-batches
  relation: related_to
  kb: pyrite
- target: coordination-task-plugin
  relation: related_to
  kb: pyrite
kind: spike
status: proposed
priority: medium
effort: L
---

## Problem

Pyrite excels at knowledge storage, indexing, and retrieval. MASFactory excels at multi-agent workflow orchestration — DAG scheduling, loop/switch control flow, parallel execution, and human-in-the-loop interaction. Currently, complex KB lifecycle workflows (populate → validate → fix → research → enrich) are orchestrated through prose instructions in skill files, interpreted by a single LLM agent.

This works, but doesn't scale to workflows that need:
- True parallel agent execution (not just parallel Claude Code subagents)
- Structured message passing between phases
- Visual workflow inspection and runtime tracing
- Reproducible, versionable workflow definitions
- Human-in-the-loop at specific decision points in the web UI

## Proposal

A **compatible fork** of MASFactory that integrates with Pyrite at the adapter boundary. MASFactory remains the orchestrator; Pyrite remains the knowledge store. The integration has three surfaces:

### 1. Pyrite as MASFactory's persistence layer

MASFactory workflows and their outputs are stored as Pyrite KB entries:

**Workflow definitions** — stored as entries in the project KB:
```yaml
---
id: kb-lifecycle-workflow-v2
type: workflow
title: "KB Lifecycle: populate → validate → fix → research"
workflow_format: masfactory
status: active
---
```
Body contains the MASFactory graph spec (JSON or YAML). Versionable via git, searchable via Pyrite index, linkable to the KBs they operate on.

**Workflow executions** — stored as task entries with execution state:
```yaml
---
id: run-goldratt-kb-20260311
type: task
title: "KB Lifecycle run: goldratt-biography"
parent: kb-lifecycle-workflow-v2
status: in_progress
agent_context:
  workflow_run_id: "run-abc123"
  current_node: "validate"
  completed_nodes: ["init-kb", "rewrite-schema", "plan-IDs", "populate-batch-1..3"]
---
```

**Workflow-produced knowledge** — entries created by MASFactory agents land in a target KB via Pyrite's standard CRUD. The workflow definition specifies the target KB.

### 2. Pyrite adapters for MASFactory

MASFactory's adapter system maps cleanly to Pyrite services:

| MASFactory Adapter | Pyrite Service | Integration |
|-------------------|----------------|-------------|
| **ContextProvider** (Memory) | SearchService (keyword, semantic, hybrid) | Query the KB index for context relevant to the current agent's task |
| **ContextProvider** (Retrieval) | GraphService (backlinks, outlinks) | Traverse the knowledge graph for related entries |
| **Tool** (MCP) | MCP server tools | All Pyrite MCP tools available to MASFactory agents |
| **Tool** (Custom) | CLI commands | `pyrite index build`, `pyrite qa validate` as CustomNodes |
| **Model** | LLMService | Share Pyrite's BYOK model configuration |

Key adapter: **PyriteContextProvider** — wraps Pyrite's search and graph services as MASFactory ContextProviders, so every agent in a workflow gets KB-aware context injection automatically.

### 3. Chat UX in Pyrite web frontend

MASFactory's Interaction nodes surface as a chat interface in Pyrite's web UI:

- **Workflow launcher** — select a workflow template, configure parameters, start execution
- **Interaction nodes** — when the workflow reaches an Interaction node, the UI shows a chat panel for user confirmation/feedback
- **DAG visualization** — show the workflow graph with node states (pending, running, completed, failed)
- **Runtime tracing** — MASFactory's hook system feeds execution events to the UI via WebSocket

This replaces VS Code as the primary MASFactory interface for Pyrite users.

### 4. Workflow-produced KB pattern

When a workflow creates knowledge, it goes to a **separate KB** (not the project KB where the workflow definition lives):

```
project-kb/
  workflows/
    kb-lifecycle-workflow-v2.md    ← workflow definition
    run-goldratt-kb-20260311.md    ← execution record

goldratt-biography/               ← workflow-produced KB
  concepts/
  people/
  events/
  ...
```

The execution record in the project KB links to the produced KB via cross-KB references. This keeps workflow metadata separate from produced knowledge.

## Implementation Approach

### Phase 1: Spike — adapter feasibility (effort: S)

- Fork MASFactory
- Implement `PyriteContextProvider` wrapping SearchService
- Implement `PyriteTool` wrapping a subset of MCP tools (kb_search, kb_read, kb_create, kb_update)
- Run one MASFactory workflow that populates a simple Pyrite KB
- Evaluate: does the adapter boundary work? What's awkward?

### Phase 2: Workflow persistence (effort: M)

- `workflow` entry type (or use existing `task` with conventions)
- Store graph specs as entry bodies
- Execution state tracked via task checkpoints
- Workflow outputs land in target KB via standard CRUD

### Phase 3: Chat UX (effort: L)

- WebSocket bridge from MASFactory hook system to Pyrite web frontend
- Interaction node rendering in chat panel
- DAG visualization component (could reuse network graph work from JI plugin)
- Workflow launcher UI

### Phase 4: Template library (effort: M)

- KB Lifecycle workflow template (parameterized by KB type)
- QA Pipeline workflow template
- Investigation workflow template (for journalism-investigation plugin)
- Template marketplace (share across Pyrite instances)

## Open Questions

1. **Fork maintenance** — How much does the fork diverge? Can we upstream Pyrite adapters to MASFactory core? The adapter pattern should minimize fork-specific code.

2. **Model routing** — MASFactory agents need LLM access. Use Pyrite's LLMService (BYOK) or MASFactory's own OpenAIModel adapter? Probably Pyrite's, for unified config.

3. **Execution environment** — MASFactory runs as a Python process. Does it run inside the Pyrite server process, as a sidecar, or as a separate service? Sidecar is simplest; in-process risks blocking the API.

4. **VibeGraph value** — Is "natural language → workflow" worth it when Claude Code already interprets skill prose? Maybe — if the output is a reusable, versionable graph spec rather than a one-shot execution. The value is in the artifact, not the generation.

5. **Conflict with native patterns** — The native workflow patterns item covers loops, checkpoints, and parallel batches at the task level. Does MASFactory integration supersede that, or do they coexist? They coexist — native patterns are for simple cases; MASFactory is for complex multi-agent orchestration.

## References

- MASFactory paper: Liu et al., arXiv:2603.06007 (March 2026)
- MASFactory code: https://github.com/BUPT-GAMMA/MASFactory
- Fork: https://github.com/markramm/MASFactory
- Analysis: `/Users/markr/tcp-kb-internal/agent_software_kb/masfactory-pyrite-analysis.md`
- Pyrite task system: [[coordination-task-plugin]]

## Acceptance Criteria (Spike — Phase 1)

- MASFactory fork builds and runs with Pyrite adapters
- PyriteContextProvider returns search results as ContextBlocks
- PyriteTool wraps kb_create/kb_update for workflow agents
- One end-to-end workflow: intent → graph → execute → KB entries created
- Written evaluation of adapter boundary fitness (what works, what's awkward, what needs core changes)
