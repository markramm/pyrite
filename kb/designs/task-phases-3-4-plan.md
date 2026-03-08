---
id: task-phases-3-4-plan
title: "Task Coordination Phases 3-4: DAG Queries + QA Integration"
type: design_doc
status: draft
tags: [design, task, agents, coordination, core]
links:
  - target: "coordination-task-plugin"
    relation: "refines"
    note: "Detailed design for phases 3 and 4"
  - target: "adr-0019"
    relation: "implements"
    note: "Kanban flow model drives pull-based task queries"
  - target: "software-project-plugin"
    relation: "related"
    note: "sw_pull_next depends on task readiness queries from phase 3"
---

# Task Coordination Phases 3-4: DAG Queries + QA Integration

## Context

Phases 1-2 delivered the core task system: `TaskEntry` model, workflow state machine, atomic CAS claiming via protocol-level `claim_entry()`, parent-child decomposition with auto-rollup, and checkpointing. All of this is now core (not a plugin), with `Parentable` and `claim_entry()` generalized as protocol-level operations.

**What works today:**
- Full task CRUD + 7 MCP tools + 7 CLI commands
- Atomic claim-or-fail (CAS on `Assignable + Statusable`)
- Workflow transition validation (`_task_validate_transition` before_save hook)
- Cascading parent auto-rollup (`_parent_rollup` after_save hook)
- Checkpoint accumulation with confidence and evidence tracking
- QA service fire-and-forget task creation on assessment failure

**What's missing:**
- Dependency-aware readiness queries (which tasks are unblocked?)
- DAG traversal (critical path, subtree, ancestors)
- Evidence aggregation from children to parent
- Blocked state auto-management
- QA task deduplication and lifecycle integration
- `task_status` enrichment (children + dependency statuses)

ADR-0019 (accepted) establishes pull-based kanban as the work model. The software-kb's `sw_pull_next` tool needs to answer "what can I work on?" — which requires readiness queries from phase 3.

---

## Phase 3: DAG Queries and Orchestrator Support

**Goal:** Enable orchestrators to reason about task graphs — what's ready, what's blocked, what's the critical path, and what evidence has been collected.

### 3A. Dependency Readiness Query

The core new primitive: "which tasks have all dependencies satisfied?"

**Implementation in `TaskService`:**

```python
def list_ready_tasks(self, kb_name: str, *, assignee: str = "") -> list[dict]:
    """Return open tasks whose dependencies are all done (or have none)."""
```

**SQL approach:** Since `dependencies` lives in `metadata` JSON, we can't do a pure SQL join. Strategy:

1. Query all `open` tasks in the KB
2. For each, extract `json_extract(metadata, '$.dependencies')`
3. If empty/null → ready
4. Else, query statuses of dependency IDs in a single batch
5. Task is ready if all deps have `status = 'done'`

This is O(1) SQL queries (batch the dep IDs into a single `IN` clause), not O(N) per task.

**MCP tool: `task_ready`** (read tier)
```
Arguments: kb_name (required), assignee (optional — filter to "my" ready tasks)
Returns: list of ready task dicts, sorted by priority desc
```

This is the query that `sw_pull_next` delegates to.

### 3B. Task Status Enrichment

`task_status` currently returns the raw entry dict. Enrich it with:

- `children`: list of child task summaries (id, title, status, assignee)
- `dependency_statuses`: dict mapping dep ID → {title, status}
- `evidence_entries`: list of evidence entry summaries (id, title, type)
- `progress_summary`: extracted from agent_context (confidence, last checkpoint time)

**Implementation:** New `get_task_detail(task_id, kb_name)` method on `TaskService` that calls `get_task` + batch-queries children/deps/evidence. The existing `get_task` stays as the thin wrapper for callers that don't need enrichment.

**MCP tool:** Update `task_status` handler to use `get_task_detail`.

### 3C. DAG Traversal Options for `task_list`

Add optional traversal parameters to `task_list`:

- `subtree_of: str` — return all descendants (children, grandchildren, ...) of a task
- `ancestors_of: str` — return the parent chain up to the root
- `blocked_by: str` — return tasks that this task depends on and are not done

**Subtree** uses a recursive approach: query children, then children of children. Since task trees are shallow (typically 2-3 levels), this is fine without CTEs.

**Ancestors** walks `parent` links upward — simple loop with max depth guard.

**Blocked-by** extracts `dependencies` from metadata, filters to non-done statuses.

### 3D. Evidence Aggregation

New method: `aggregate_evidence(task_id, kb_name) -> list[str]`

Collects `evidence` lists from a task and all its descendants (subtree). Returns deduplicated list of evidence entry IDs. This feeds the orchestrator's "what did this investigation produce?" query.

**Integration with rollup:** When `_parent_rollup` auto-completes a parent, also merge children's evidence into the parent's evidence list. This makes evidence "bubble up" automatically — the orchestrator only needs to check the root task.

### 3E. Dependency-Aware Blocking Hook

New core hook: `_dependency_block_check` (after_save)

When a task transitions to `blocked` or `failed`:
1. Find tasks that list this task in their `dependencies`
2. If any dependent task is `in_progress`, auto-transition it to `blocked`

When a task transitions to `done`:
1. Find tasks that list this task in their `dependencies`
2. For each, check if ALL dependencies are now `done`
3. If so and the task is `blocked`, auto-transition to `in_progress` (or `open` if it was never started)

**SQL for "find dependents":** `SELECT id FROM entry WHERE json_extract(metadata, '$.dependencies') LIKE '%' || :task_id || '%'` — imprecise but fast. Confirm with JSON extraction in Python.

### 3F. `decompose_task` Enhancement

Thread `dependencies` through child specs in `decompose_task`:

```python
children = [
    {"title": "Step 1"},
    {"title": "Step 2", "dependencies": ["step-1-id"]},
    {"title": "Step 3", "dependencies": ["step-1-id", "step-2-id"]},
]
```

This enables orchestrators to express sequential subtask chains in a single call.

### Phase 3 File Changes

| File | Change |
|------|--------|
| `pyrite/services/task_service.py` | Add `list_ready_tasks()`, `get_task_detail()`, `aggregate_evidence()`. Enhance `list_tasks()` with subtree/ancestors/blocked_by params. Thread `dependencies` through `decompose_task`. |
| `pyrite/services/kb_service.py` | Add `_dependency_block_check` to `_CORE_HOOKS["after_save"]`. Enhance `_parent_rollup` to merge evidence on rollup. |
| `pyrite/server/tool_schemas.py` | Add `task_ready` to READ_TOOLS. Add traversal params to `task_list`. Add `dependencies` to `task_decompose` child schema. Add `evidence`/`dependencies` to `task_update`. |
| `pyrite/server/mcp_server.py` | Add `_task_ready` handler. Update `_task_status` to use `get_task_detail`. Update `_task_list` with traversal params. |
| `pyrite/cli/task_commands.py` | Add `ready` subcommand. Add `--subtree`/`--ancestors` flags to `list`. |
| `tests/test_task_service.py` | Add `TestReadyTasks`, `TestDAGTraversal`, `TestEvidenceAggregation`, `TestDependencyBlocking` test classes. |
| `tests/test_task.py` | Add `TestDecomposeWithDeps` tests. |

### Phase 3 Effort: L (large)

Build order: 3A → 3B → 3C → 3D → 3E → 3F (3A-3D can parallelize after 3A is done)

---

## Phase 4: QA Agent Integration

**Goal:** QA validation becomes a first-class task workflow. QA tasks are created, claimed, tracked, and completed through the same coordination infrastructure as all other work.

### 4A. QA Task Lifecycle

Replace the fire-and-forget `_maybe_create_task` with a proper lifecycle:

1. **Deduplication:** Before creating a QA task, check if an open/claimed/in_progress QA task already exists for the same `target_entry`. Use a query: `list_tasks(kb_name, tags=["qa"], target_entry=entry_id)` (needs metadata filter).
2. **Structured creation:** QA tasks get:
   - `parent`: optional, if the entry was produced by a known parent task
   - `dependencies`: the target entry ID (task depends on the entry existing)
   - `evidence`: assessment entry ID linked immediately
   - `tags`: `["qa", "auto-generated"]`
   - `agent_context.target_entry`: the entry being validated
   - `agent_context.assessment_id`: the triggering assessment
3. **Completion:** When a QA task is marked `done`, link the resolution back to the assessment (update assessment status to `resolved`).

### 4B. Assessment-Task Linking

Bidirectional linking between QA assessments and QA tasks:

- Assessment entry gets `task_id` in metadata → "which task tracks fixing this?"
- Task entry gets assessment ID in evidence → "what assessment triggered this?"

New method: `link_assessment_to_task(assessment_id, task_id, kb_name)` on QA service.

### 4C. "Entries Needing QA" Query

New MCP tool: `qa_pending` (read tier)

Returns entries that need QA attention, prioritized:
1. Entries with failed assessments and no open QA task (need task creation)
2. Entries with open QA tasks (in progress)
3. Entries never assessed (need initial assessment)
4. Entries with stale assessments (older than configurable threshold)

This is the QA agent's equivalent of `task_ready` — "what should I work on next?"

### 4D. QA Workflow as Task Pipeline

The full QA agent workflow becomes:

```
1. qa_pending → get next entry needing QA
2. task_create (or reuse existing) → QA task for the entry
3. task_claim → atomic claim by QA agent
4. assess_entry → run validation + LLM assessment
5. task_checkpoint → record assessment results
6. If pass: task_update status=done, evidence=[assessment_id]
7. If fail: task_update status=review (needs human attention)
   OR: task_decompose → create fix-subtasks for each issue
```

This makes QA progress fully visible through `task_list(tags=["qa"])`.

### 4E. Auto-QA Hook

New core hook: `_auto_qa_check` (after_save)

When a non-QA entry is created or updated in a KB that has QA enabled:
- If the entry has no recent assessment → create a QA task (deduplicated)
- Configurable per-KB via KB config: `qa_auto_create_tasks: true`

This replaces the manual `create_task_on_fail` flag with a systematic approach.

### Phase 4 File Changes

| File | Change |
|------|--------|
| `pyrite/services/qa_service.py` | Replace `_maybe_create_task` with `create_qa_task()` (deduplication, structured linking). Add `link_assessment_to_task()`. Add `get_pending_qa()` query. |
| `pyrite/services/task_service.py` | Add `list_tasks` filter by `tags` (metadata query). |
| `pyrite/services/kb_service.py` | Add `_auto_qa_check` to `_CORE_HOOKS["after_save"]` (optional, config-gated). |
| `pyrite/server/tool_schemas.py` | Add `qa_pending` to READ_TOOLS. Update `kb_qa_assess` description. |
| `pyrite/server/mcp_server.py` | Add `_qa_pending` handler. |
| `pyrite/cli/__init__.py` | Add `qa pending` subcommand (if not already present). |
| `tests/test_qa_service.py` | Add `TestQATaskLifecycle`, `TestAssessmentTaskLinking`, `TestPendingQA`, `TestDeduplication` test classes. |
| `tests/test_task_service.py` | Add `TestListByTags` tests. |

### Phase 4 Effort: M (medium)

Build order: 4A → 4B → 4C → 4D → 4E (4A is the foundation, rest builds on it)

---

## Cross-Phase Dependencies

```
Phase 3A (readiness query)  ──→  sw_pull_next (software-kb Wave 2)
Phase 3B (task enrichment)  ──→  sw_context_for_item (assembles task + KB context)
Phase 3D (evidence rollup)  ──→  Phase 4B (assessment linking)
Phase 3E (dep blocking)     ──→  Phase 4D (QA pipeline auto-blocking)
Phase 4C (qa_pending)       ──→  QA agent autonomous workflow
```

Phase 3A is the critical enabler for `sw_pull_next` — the software-kb's kanban pull tool (ADR-0019). This should be built first.

## Verification

```bash
# Phase 3
.venv/bin/pytest tests/test_task_service.py -k "ready or dag or evidence or blocking" -v
.venv/bin/pyrite task ready --kb <kb>
.venv/bin/pyrite task list --subtree-of <parent_id> --kb <kb>

# Phase 4
.venv/bin/pytest tests/test_qa_service.py -k "qa_task or pending or dedup" -v
.venv/bin/pyrite qa pending --kb <kb>

# Full regression
.venv/bin/pytest tests/ -v --tb=short
```
