---
id: coordination-task-plugin
title: Coordination/Task Plugin
type: backlog_item
tags:
- feature
- extension
- plugin
- agent-infrastructure
kind: feature
priority: medium
status: proposed
effort: XL
---

## Problem

There is no structured way to track work items, assignments, or evidence chains within the knowledge graph. Tasks currently live outside Pyrite (GitHub issues, TODO comments) disconnected from the knowledge they produce.

More critically: in an agent swarm world, the coordination primitive is the task. An orchestrator decomposes a research question into subtasks, dispatches them across agents, and aggregates results. Without a task system, agents have no shared understanding of what's been done, what's in progress, and what's blocked.

## Design Philosophy

This is **not a lightweight Jira inside Pyrite.** It is a **coordination primitive for agent swarms.** The design optimizes for programmatic consumers (agents claiming tasks, reporting evidence, querying the DAG) rather than humans managing a kanban board.

Tasks live in the same graph as the knowledge they produce. A task "Research actor X" links to the person entry it creates. This makes provenance traceable — you can always ask "why does this entry exist?" and follow links back to the task that spawned it.

## Proposed Solution

### Entry Type: `task`

```yaml
---
id: research-actor-x
type: task
title: "Research Actor X"
status: in_progress
assignee: "agent:claude-code-7a3f"
parent_task: decompose-org-y
dependencies:
  - gather-public-records
evidence:
  - actor-x-person-entry
  - org-y-connection-doc
priority: 7
due_date: 2026-03-15
agent_context:
  capabilities: [web-search, kb-write]
  confidence: 0.85
  checkpoint: "Found 3 public records, analyzing connections"
---

## Task Description

Research Actor X's role in Organization Y. Produce a person entry with affiliations, timeline, and sourced claims.

## Progress Log

- 2026-02-28T14:00Z: Claimed by agent:claude-code-7a3f
- 2026-02-28T14:05Z: Found 3 public records via web search
- 2026-02-28T14:12Z: Created draft person entry [[actor-x-person-entry]]
```

### Field definitions

- `status`: enum (open, claimed, in_progress, blocked, review, done, failed)
- `assignee`: structured agent identity (not just a string)
- `parent_task`: entry ID of the parent task (for hierarchical decomposition)
- `dependencies`: array of entry IDs (tasks that must complete first)
- `evidence`: array of entry IDs (knowledge entries that support/fulfill this task)
- `priority`: int 1-10
- `due_date`: optional date
- `agent_context`: dict with agent capabilities, confidence, and checkpoint state

### Hierarchical Tasks

Parent/child relationships with rollup semantics:

- A parent task's status is **derived** from its children (all done → parent done; any failed → parent blocked)
- Evidence **aggregates upward** — the parent task's evidence includes all children's evidence
- The orchestrator can query the task DAG: "what's the critical path?", "what's blocked and why?", "which subtree can I parallelize?"

### MCP Tools

**Read tier:**
- `task_list` — query by status/assignee/priority/parent, returns DAG structure
- `task_status` — get task with children, dependencies, evidence, progress log
- `task_critical_path` — identify blocking chain in the task DAG

**Write tier:**
- `task_create` — create a task (or subtask of a parent)
- `task_claim` — atomic claim-or-fail (compare-and-swap on status, prevents two agents claiming the same task)
- `task_checkpoint` — append to progress log with intermediate findings
- `task_complete` — mark done with evidence links
- `task_fail` — mark failed with reason
- `task_flag` — flag for human review with reason
- `task_decompose` — create child tasks from a parent (bulk create with parent link)

### Atomic Operations

`task_claim` must be a compare-and-swap, not a read-then-write. In a concurrent swarm, two agents reading "open" and both writing "claimed" is a race condition. Implementation: SQLite's `UPDATE ... WHERE status = 'open'` returns affected row count — if 0, the claim failed.

### Agent Identity

The `assignee` field uses structured agent identity:

```yaml
assignee: "agent:claude-code-7a3f"
agent_context:
  runtime: "claude-code"
  session_id: "7a3f"
  capabilities: [web-search, kb-write, kb-read]
  model: "claude-sonnet-4"
```

This feeds the provenance story — when reviewing agent-authored KB entries, you can trace back to which agent wrote them, what task they were working on, and what capabilities they had.

### Progress and Checkpoints

Long-running agent tasks need intermediate state. An agent researching a complex topic produces partial findings before completing. The append-only progress log lets orchestrators monitor without polling:

```
task_checkpoint(
  task_id="research-actor-x",
  message="Found 3 public records, analyzing connections",
  confidence=0.85,
  partial_evidence=["public-records-search-result"]
)
```

### Lifecycle Hooks

- `before_save`: validate status transitions via workflow state machine (no skipping from open to done)
- `after_save`: auto-link evidence entries back to the task; update parent task status rollup
- `after_save`: auto-unblock tasks when dependencies complete
- `before_delete`: prevent deleting tasks with active children

### Workflow State Machine

```python
TASK_WORKFLOW = {
    "states": ["open", "claimed", "in_progress", "blocked", "review", "done", "failed"],
    "initial": "open",
    "field": "status",
    "transitions": [
        {"from": "open", "to": "claimed", "requires": "write"},
        {"from": "claimed", "to": "in_progress", "requires": "write"},
        {"from": "in_progress", "to": "blocked", "requires": "write"},
        {"from": "in_progress", "to": "review", "requires": "write"},
        {"from": "in_progress", "to": "done", "requires": "write"},
        {"from": "in_progress", "to": "failed", "requires": "write"},
        {"from": "blocked", "to": "in_progress", "requires": "write"},
        {"from": "review", "to": "done", "requires": "write"},
        {"from": "review", "to": "in_progress", "requires": "write"},
        {"from": "failed", "to": "open", "requires": "write", "requires_reason": True},
    ],
}
```

## Phases

### Phase 1: Core task type and CLI (effort: M)

- `TaskEntry` dataclass with all fields
- Workflow state machine for status transitions
- CLI: `pyrite task list`, `pyrite task create`, `pyrite task status`
- Basic validators (status transitions, dependency resolution)
- Tests: 8-section structure

### Phase 2: MCP tools and atomic operations (effort: M)

- All MCP tools listed above
- Atomic `task_claim` with compare-and-swap
- `task_decompose` for bulk subtask creation
- `task_checkpoint` for progress reporting

### Phase 3: DAG queries and orchestrator support (effort: L)

- `task_critical_path` — blocking chain analysis
- Parent status rollup (derived from children)
- Evidence aggregation up the tree
- `task_list` with DAG traversal options (subtree, ancestors, blocked-by)

### Phase 4: Integration with QA agent (effort: M)

- QA validation tasks auto-created on entry save
- QA assessment entries linked as task evidence
- "Entries needing QA" as a task query

## Relationship to QA Agent

The QA agent (backlog #73) is already a single-purpose agent workflow — it validates entries and produces assessment entries. With the task plugin, the QA agent can be implemented *on top of it*: create QA tasks, claim them, link assessments as evidence, complete them. This makes QA progress trackable and queryable through the same task infrastructure.

## Related

- [[bhag-self-configuring-knowledge-infrastructure]] — Task coordination is core to the agent swarm vision
- [[qa-agent-workflows]] — QA agent as a consumer of the task system
- [[pyrite/plugins/protocol.py]] — PyritePlugin protocol (workflows, hooks, MCP tools)
- [[extensions/]] — Existing extension patterns (zettelkasten, encyclopedia workflows)
