---
id: coordination-task-plugin
title: Coordination/Task System (Core)
type: backlog_item
tags:
- feature
- core
- agent-infrastructure
kind: feature
status: review
effort: XL
---

## Problem

There is no structured way to track work items, assignments, or evidence chains within the knowledge graph. Tasks currently live outside Pyrite (GitHub issues, TODO comments) disconnected from the knowledge they produce.

More critically: in an agent swarm world, the coordination primitive is the task. An orchestrator decomposes a research question into subtasks, dispatches them across agents, and aggregates results. Without a task system, agents have no shared understanding of what's been done, what's in progress, and what's blocked.

## Design Philosophy

This is **not a lightweight Jira inside Pyrite.** It is a **coordination primitive for agent swarms.** The design optimizes for programmatic consumers (agents claiming tasks, reporting evidence, querying the DAG) rather than humans managing a kanban board.

Tasks live in the same graph as the knowledge they produce. A task "Research actor X" links to the person entry it creates. This makes provenance traceable — you can always ask "why does this entry exist?" and follow links back to the task that spawned it.

## Implementation

### Entry Type: `task`

```yaml
---
id: research-actor-x
type: task
title: "Research Actor X"
status: in_progress
assignee: "agent:claude-code-7a3f"
parent: decompose-org-y
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
```

### Field definitions

- `status`: enum (open, claimed, in_progress, blocked, review, done, failed)
- `assignee`: structured agent identity (not just a string)
- `parent`: entry ID of the parent task (via `Parentable` protocol — generalized to any entry type)
- `dependencies`: array of entry IDs (tasks that must complete first)
- `evidence`: array of entry IDs (knowledge entries that support/fulfill this task)
- `priority`: int 1-10
- `due_date`: optional date
- `agent_context`: dict with agent capabilities, confidence, and checkpoint state

### Protocol-Level Generalization

As of the core migration (2026-03-08), several task primitives were generalized to protocol-level platform operations:

- **`Parentable` protocol mixin** — Any entry type can have `parent: str` for hierarchical relationships. Registered in `PROTOCOL_REGISTRY`, `PROTOCOL_FIELDS`, `PROTOCOL_COLUMN_KEYS`.
- **`claim_entry()` on KBService** — Atomic CAS for any `Assignable + Statusable` entry, not just tasks. `TaskService.claim_task()` delegates to it.
- **Core hooks in `_CORE_HOOKS`** — `_task_validate_transition` (before_save) enforces workflow state machine; `_parent_rollup` (after_save) auto-completes any `Statusable + Parentable` parent when all children reach terminal status.

### MCP Tools

**Read tier:**
- `task_list` — query by status/assignee/priority/parent
- `task_status` — get task with children, dependencies, evidence, progress log

**Write tier:**
- `task_create` — create a task (or subtask of a parent)
- `task_update` — update task fields with workflow validation
- `task_claim` — atomic claim-or-fail (compare-and-swap on status)
- `task_checkpoint` — append to progress log with intermediate findings
- `task_decompose` — create child tasks from a parent (bulk create with parent link)

### Workflow State Machine

```python
TASK_WORKFLOW = {
    "open": ["claimed"],
    "claimed": ["in_progress", "open"],
    "in_progress": ["blocked", "review", "done", "failed"],
    "blocked": ["in_progress"],
    "review": ["done", "in_progress"],
    "failed": ["open"],  # requires reason
    "done": [],
}
```

## Phases

### Phase 1: Core task type and CLI (effort: M) — done

Delivered:
- `TaskEntry` dataclass in `pyrite/models/task.py` with all fields
- `Parentable` protocol mixin in `pyrite/models/protocols.py`
- Workflow state machine with `TASK_WORKFLOW`, `get_allowed_transitions()`, `can_transition()`
- Validators in `pyrite/models/task_validators.py`
- CLI: 7 commands via `pyrite/cli/task_commands.py`
- `TASK_KB_PRESET` for task-board template
- Registered in `ENTRY_TYPE_REGISTRY` via `models/__init__.py`

### Phase 2: MCP tools and atomic operations (effort: M) — done

Delivered:
- `TaskService` in `pyrite/services/task_service.py` — wraps KBService
- 7 MCP tools in `pyrite/server/tool_schemas.py` + handlers in `mcp_server.py`
- Protocol-level `claim_entry()` on KBService with atomic CAS
- `task_decompose` for bulk subtask creation with parent linking
- `task_checkpoint` with timestamped progress logging, confidence tracking, evidence accumulation
- Parent auto-rollup with cascading via `_parent_rollup` core hook
- Workflow transition validation via `_task_validate_transition` core hook
- Core relationship types (`subtask_of`/`has_subtask`, `produces`/`produced_by`) in registry
- QA service hard-imports TaskService (no more soft import)
- Old `extensions/task/` deleted — everything is core
- 2094 tests passing (39 new task-specific tests)

### Phase 3: DAG queries and orchestrator support (effort: L)

- `task_critical_path` — blocking chain analysis via dependency graph traversal
- Evidence aggregation up the tree (parent collects children's evidence links)
- `task_list` with DAG traversal options (subtree, ancestors, blocked-by)
- Dependency-aware unblocking: auto-transition blocked→in_progress when deps complete

### Phase 4: Integration with QA agent (effort: M)

- QA validation tasks auto-created on entry save
- QA assessment entries linked as task evidence
- "Entries needing QA" as a task query
- QA agent workflow built on top of task primitives (claim → validate → checkpoint → complete)

## Related

- [[bhag-self-configuring-knowledge-infrastructure]] — Task coordination is core to the agent swarm vision
- [[qa-agent-workflows]] — QA agent as a consumer of the task system
- [[adr-0019]] — Pull-based kanban workflow for agent teams
