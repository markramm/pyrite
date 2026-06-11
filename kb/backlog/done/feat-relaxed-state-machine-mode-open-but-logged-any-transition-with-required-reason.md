---
id: feat-relaxed-state-machine-mode-open-but-logged-any-transition-with-required-reason
title: "FEATURE PROPOSAL (Mark direction 2026-06-10, from investigation-conductor session)"
type: backlog_item
tags: [bug, conductor-filed, cli, task-system]
importance: 5
kind: feature
status: done
priority: high
effort: S
rank: 1175
---

FEATURE: per-entity-type RELAXED state-machine MODE. Separate two checks the machine currently conflates: (1) is `status` a member of the allowed STATE SET — always enforce (cheap; catches typos; keeps index queryable); (2) is this TRANSITION legal given current state — make CONFIGURABLE PER ENTITY TYPE.

THE ONE INVARIANT TO KEEP: `open->claimed` stays an ATOMIC compare-and-swap regardless of mode (concurrency guard, not a lifecycle rule; lives outside the transition table).

MOTIVATION (friction observed every conductor tick): (a) conductor cannot triage an UNCLAIMED task `open->blocked` without a workaround; (b) subsumes `issue-add-held-state` — no 'held' enum needed: `status:blocked` + `status_reason:"deliverables-met, awaiting GAO docket"` is more expressive than any fixed state; (c) reason-on-every-transition under relaxed mode, uniform, no happy-path exemption (exempting "obvious" transitions smuggles a mini transition-table back in). Reason field is what makes a git diff legible weeks later.

## Design (LOCKED 2026-06-11 by Mark)

**Reading C — per-entity-type config.** The `enforce_transitions` and `require_reason_on_transition` toggles live on the **entry type definition itself**, not on the KB config. A KB that holds both strict `task`s and relaxed `sw_ticket`s is fine — schema travels with the entity.

### Concrete shape

In `pyrite/models/task.py`, the existing `TASK_WORKFLOW` dict grows:

```python
TASK_WORKFLOW = {
    "states": ["open", "claimed", ...],
    "initial": "open",
    "field": "status",
    "transitions": [...],
    # New, Tier A r1175:
    "enforce_transitions": True,       # strict by default for core tasks
    "require_reason_on_transition": False,
    "atomic_claim": True,              # always; lives outside the toggle
}
```

A plugin's `sw_ticket` (or similar) type schema can declare its own:

```yaml
# software-kb's sw_ticket schema
state_machine:
  states: [open, claimed, in_progress, review, blocked, done, failed]
  initial: open
  field: status
  enforce_transitions: false
  require_reason_on_transition: true
```

### Behavior matrix

| `enforce_transitions` | `require_reason_on_transition` | Effect |
|---|---|---|
| true | false (current) | Strict workflow — only declared transitions allowed |
| false | true | Any status in `states` allowed iff `status_reason` is set |
| false | false | Any status in `states` allowed, no reason required (unlikely default) |
| true | true | Strict workflow + require reason on every transition (audit-heavy) |

`_task_validate_transition` (in `pyrite/services/task_service.py:576`) reads the type's `state_machine` config (falling back to the core `TASK_WORKFLOW` for `task` type), then dispatches.

`open->claimed` always goes through atomic CAS regardless of mode.

### `status_reason` shape — v1

**Free string** for v1 (e.g., `status_reason: "awaiting GAO docket"`). Entry-ref (`status_reason: [[awaiting-gao-docket]]`) is a follow-up enrichment that doesn't break compat — a wikilink in a free-string field still renders and indexes correctly; the upgrade path is just adding ref-resolution validation later.

### Backward compatibility — migration script

New CLI: `pyrite task migrate-relaxed-mode <kb> [--dry-run]`. Walks every task in the KB whose entry-type declares `enforce_transitions=false` AND `require_reason_on_transition=true`, and backfills `status_reason: "pre-relaxed-mode"` for any task missing the field. Idempotent. Reports count of tasks migrated.

### CLI

`pyrite task update <id> -f status=blocked --reason "awaiting GAO"` — `--reason` flag, with `--status-reason` as alias to match the frontmatter field name.

### Retire `issue-add-held-state`

In the same commit that lands this feature, mark `issue-add-held-state-to-pyrite-task-state-machine` as `wont_do` with note "subsumed by Tier A r1175 relaxed-mode per-entity-type config."

### Concurrency

`open->claimed` is ALWAYS atomic CAS, regardless of mode. The relaxed-mode dispatch must NOT touch this path. Verified in `pyrite/services/task_service.py` — keep the existing claim transaction.

## Acceptance criteria

- `state_machine` config block on the `task` entry type with the four keys: `states`, `transitions`, `enforce_transitions`, `require_reason_on_transition`. Defaults: strict (`enforce_transitions=true`, `require_reason_on_transition=false`) so existing tasks unchanged.
- Plugins can override the block on their own entry types (e.g., `software-kb`'s `sw_ticket`).
- `_task_validate_transition` reads the type's config and dispatches: strict path uses the existing transition table; relaxed path validates only `status in states` AND `status_reason` is non-empty.
- `--reason` flag on `pyrite task update` writes `status_reason` to frontmatter.
- `pyrite task migrate-relaxed-mode <kb> [--dry-run]` backfills `status_reason` for existing tasks of relaxed-mode types.
- `open->claimed` remains an atomic CAS in BOTH modes (preserve existing claim transaction).
- `issue-add-held-state-to-pyrite-task-state-machine` retired (`wont_do`) in the same commit.
- Tests cover: (a) strict-mode rejection of bad transition (regression — existing behavior); (b) relaxed-mode acceptance of any state-set member with reason; (c) relaxed-mode rejection without reason; (d) `open->claimed` atomicity in both modes; (e) migration script backfill + idempotency.

## Implementation arc

Estimated ~4 fires:
1. RED tests for state_machine config plumbing + relaxed-mode dispatch
2. GREEN: `_task_validate_transition` reads per-type config; relaxed-mode path; `--reason` CLI flag
3. Migration script `pyrite task migrate-relaxed-mode` + tests
4. Retire `issue-add-held-state`; documentation note in task service component doc

## Owner / related

Owner: pyrite repo. Subsumes `issue-add-held-state-to-pyrite-task-state-machine`. Related to the `feat-editorial-notes-sidecar` conductor-friction family (both came out of the 2026-06-10 conductor session).
