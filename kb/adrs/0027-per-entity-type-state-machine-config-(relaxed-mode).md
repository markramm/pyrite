---
id: adr-0027
type: adr
title: "Per-Entity-Type State Machine Config (Relaxed Mode)"
adr_number: 27
status: accepted
date: 2026-06-11
deciders: ["markr"]
tags: [architecture, workflow, tasks, state-machine, plugins]
links:
  - target: "adr-0019"
    relation: "refines"
    note: "Refines the kanban workflow model with per-type state-machine config"
  - target: "adr-0021"
    relation: "refines"
    note: "Definition of Ready/Done gates remain orthogonal; this ADR only governs the transition machinery"
---

# ADR-0027: Per-Entity-Type State Machine Config (Relaxed Mode)

## Context

`pyrite/models/task.py:TASK_WORKFLOW` declares a strict transition table —
`open → claimed → in_progress → done/blocked/review/failed` — enforced
by the `_task_validate_transition` hook on every task update. Three
sources of friction surfaced in 2026-06-10's investigation-conductor
session:

- **The conductor cannot triage an unclaimed task `open → blocked`**.
  No declared transition allows it, so triage requires either
  claim-then-block (consumes the atomicity guarantee for what's a
  grooming move) or a hand-edit of frontmatter (bypasses validation
  entirely).
- **`status: blocked` carries no reason field**. A task is blocked
  because something specific happened — "awaiting GAO docket",
  "deliverables met, waiting on legal", "Substack editor parked it"
  — but the canonical state machine forgets the cause within one git
  commit. The proposed `held` enum (`issue-add-held-state`) addresses
  the symptom by inventing a sibling status, not the root cause
  (no structured place for the cause).
- **Different entry types want different machines**. The core `task`
  type is fine with strict transitions for the agent-team kanban
  workflow. A plugin-defined `sw_ticket` may want every transition
  audited via a required reason and no fixed graph (more like a
  Kanban-with-WIP-tracking shape). Both should coexist in the same
  KB.

Two earlier rejected directions: (a) **delete the transition table
entirely** loses the typo-catching that strict mode provides and
makes the `pyrite task list --status` queries semantically slippery;
(b) **per-KB toggle** treats the question as a container-level
configuration when it's structurally a type-level one — a KB with
both strict `task`s and relaxed `sw_ticket`s is a real case.

## Decision

Add per-entity-type `state_machine` config that overrides the core
`TASK_WORKFLOW`. The config block lives on the entry type's
`TypeSchema` (Reading C in the locked design — schema travels with
the entity, not the container).

### Shape

The existing `TASK_WORKFLOW` dict in `pyrite/models/task.py` gains
two configuration keys:

```python
TASK_WORKFLOW = {
    "states": [...],
    "initial": "open",
    "field": "status",
    "transitions": [...],
    "enforce_transitions": True,       # strict by default
    "require_reason_on_transition": False,
    "atomic_claim": True,              # always; lives outside the toggle
}
```

A plugin or KB declares its own:

```yaml
# software-kb's sw_ticket type schema
types:
  sw_ticket:
    state_machine:
      states: [open, claimed, in_progress, review, blocked, done, failed]
      initial: open
      field: status
      transitions: []                # ignored under relaxed mode
      enforce_transitions: false
      require_reason_on_transition: true
```

### Behavior

`validate_status_change(workflow, old_status, new_status,
status_reason, user_role)` (in `pyrite/models/task.py`) dispatches on
`workflow["enforce_transitions"]`:

- **Strict** (`enforce_transitions=True`, default): transition must be
  declared in `transitions` table. Reason required only when the
  matching transition declares `requires_reason: True` (existing
  behavior — back-compat).
- **Relaxed** (`enforce_transitions=False`): any `new_status` that's
  in `states` is accepted, IFF `status_reason` is non-empty (when
  `require_reason_on_transition=True`).

Loosens transitions but NOT state membership. Typos in `status` still
fail in both modes (`hung` ≠ `done`), which keeps `pyrite task list
--status done` queryable.

### Per-type resolution

`_task_validate_transition` calls
`resolve_workflow_for_type(entry_type, kb_schema)` to find the
workflow. The resolver returns `TASK_WORKFLOW` for the core `task`
type and any type with no `state_machine` block on its `TypeSchema`;
otherwise the type's own dict. The hook fires for the core `task`
type OR any type with a `state_machine` override — plugins opt their
own types in just by declaring the block.

### Atomic claim invariant

`open → claimed` remains an atomic compare-and-swap **at the
repo/db layer** in both modes. The state-machine config does not
touch this path; `claim_task` enforces concurrency directly. The
validator accepts `open → claimed` in both modes (strict via the
declared transition, relaxed via state-set membership), so the
atomic CAS is reachable.

### Reason field shape

`status_reason: str = ""` lives on `TaskEntry`, round-trips through
frontmatter via `to_frontmatter` / `from_frontmatter`, and is lifted
to the top of the projected entry dict by `_entry_to_dict` (matching
the rank/effort/kind lift from ADR-0026 / Tier A r1200).

**Free string for v1**. Entry-reference (`status_reason:
[[awaiting-gao-docket]]`) is a future enrichment that doesn't break
compat — a wikilink in a free-string field still renders and
indexes; the upgrade path is adding ref-resolution validation. Per
the locked design we ship the simpler shape first.

### CLI surface

`pyrite task update <id> -f status=blocked --reason "awaiting GAO"`.
`--reason` is the canonical flag with `--status-reason` as an alias
matching the frontmatter field name.

### Migration

`pyrite task migrate-relaxed-mode <kb> [--dry-run]` walks every task
in the KB, resolves each one's workflow, and stamps
`status_reason='pre-relaxed-mode'` on tasks of relaxed-reason types
that lack a reason. Idempotent. The migration is per-KB because the
type resolution depends on the KB schema.

### Subsumed work

The proposed `issue-add-held-state-to-pyrite-task-state-machine`
ticket is **subsumed by this decision**. A held entry isn't a new
state — it's `status: blocked` with `status_reason: "awaiting <X>"`,
which is structurally more expressive than any fixed enum. That
ticket is retired (`wont_do`) in the same commit that closes
r1175.

## Consequences

**Easier:**

- The conductor can do `pyrite task update <id> -f status=blocked
  --reason "awaiting GAO docket"` on an unclaimed task without
  cycling through `claimed`. Triage moves don't burn the atomic-claim
  guarantee.
- Plugin-defined entry types (e.g. `sw_ticket`) get their own
  workflow without forking the dispatch hook or copy-pasting
  `_task_validate_transition`.
- Reading a task's history through `git log` carries the audit trail
  in the frontmatter (`status_reason`), not just the diff — visible
  in three months when the original Slack thread is gone.
- The Definition of Ready/Done gates (ADR-0021) compose cleanly with
  this: a transition's reason explains *why* the gate held or
  released.

**More difficult:**

- Two transition modes mean two code paths. Strict-mode regressions
  and relaxed-mode behavior are both pinned by `TestValidateStatusChange`
  in `tests/test_task.py`, but a future contributor needs to think
  about both modes when they touch the hook.
- The `state_machine` block is YAML now and not part of `TypeSchema`'s
  declared `fields` schema — it's a free dict. If we accumulate more
  type-level config we should consider a `TypeConfig` shape that
  parses these blocks structurally rather than leaving them as
  opaque `dict[str, Any]`.
- The migration script writes `pre-relaxed-mode` as a literal string.
  When entry-reference shape lands later, those literals will need
  to be either upgraded to `[[pre-relaxed-mode]]` (which requires the
  entity to exist) or grandfathered as legacy strings the new
  validator accepts. Plan that upgrade path as part of the
  entry-ref-shape follow-up.

**No-ops:**

- Existing tasks unchanged. `TASK_WORKFLOW` defaults to
  `enforce_transitions=True`, `require_reason_on_transition=False`,
  exactly the pre-r1175 behavior. Every existing task save/update
  goes through the same strict path.

## Implementation

Landed across four commits in the Tier A r1175 arc:

- `a8517d9` (fire 1) — RED tests for `validate_status_change`
- `359be90` (fire 2) — `validate_status_change` + hook dispatch +
  `status_reason` field + `--reason` CLI flag
- `1cac8cb` (fire 3) — per-type resolver + migration script + CLI
  command + `_entry_to_dict` projection lift
- (fire 4 — this commit) — `issue-add-held-state` retirement + this
  ADR + r1175 marked done

Tests: 9 in `TestValidateStatusChange`, 4 in
`TestResolveWorkflowForType`, 5 in `TestMigrateRelaxedMode`. All
GREEN against the existing 95-test task surface.

## Related

- `feat-relaxed-state-machine-mode-open-but-logged-any-transition-with-required-reason`
  (closes via this work)
- `issue-add-held-state-to-pyrite-task-state-machine` (retired
  `wont_do`, subsumed by this decision)
- ADR-0019 Pull-Based Kanban Workflow Over Sprint Iterations (this
  refines the workflow primitive)
- ADR-0021 Definition of Ready/Done Gates (orthogonal — gates are
  evaluated separately from the transition machinery)
- Future: entry-reference shape for `status_reason` — accumulates
  reasons as graph nodes with their own backlinks and notes
