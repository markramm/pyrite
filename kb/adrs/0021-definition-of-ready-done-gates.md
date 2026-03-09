---
id: adr-0021
type: adr
title: "Definition of Ready / Definition of Done Gates"
adr_number: 21
status: accepted
date: 2026-03-09
deciders: [markr]
tags: [kanban, software-kb, quality, workflow]
links:
  - target: adr-0020
    relation: refines
  - target: definition-of-ready-done
    relation: implements
  - target: epic-software-kb-quality-gates-and-rubric-automation
    relation: tracks
---

# ADR-0021: Definition of Ready / Definition of Done Gates

## Context

The kanban workflow (ADR-0019, ADR-0020) provides state machine transitions and WIP limits, but lacks quality gates — checklists that ensure items are well-defined before work starts (Definition of Ready) and properly finished before closing (Definition of Done).

Worker agents benefit from seeing these criteria at claim time and transition time. Without gates, agents start under-specified work and produce incomplete results.

## Decision

Add configurable quality gates to `board.yaml` that are evaluated during `sw_transition` and `sw_claim`. Gates are keyed by the **target status** of a transition.

### Gate Configuration

Gates live in `board.yaml` under a `gates` key:

```yaml
gates:
  in_progress:
    name: Definition of Ready
    policy: warn  # or "enforce"
    criteria:
      - text: "Problem statement is clear and specific"
        type: judgment
      - text: "Effort estimated"
        checker: has_field
        params: { field: effort }
      - text: "Not oversized (XL+) without subtasks"
        checker: not_oversized
  done:
    name: Definition of Done
    policy: warn
    criteria:
      - text: "Tests passing"
        type: agent_responsibility
```

### Criterion Types

1. **`checker`** — References a named rubric checker function. Auto-evaluated, produces pass/fail. The `checker` key names a function from the `NAMED_CHECKERS` registry or a plugin-registered checker.

2. **`judgment`** — Surfaced to agents as guidance but always passes. Cannot be automatically verified (e.g., "problem statement is clear"). Agents are expected to self-evaluate.

3. **`agent_responsibility`** — Like judgment, but specifically marks things the agent must verify itself (e.g., "tests passing"). Always passes in gate evaluation.

### Policies

- **`warn`** (default): Gate failures are included in the response but do not block the transition. Agents see what they should address.
- **`enforce`**: Gate failures block the transition. The agent must fix issues before proceeding.

### Evaluation Points

- `sw_claim` evaluates the gate for `in_progress` (DoR)
- `sw_transition` evaluates the gate for the target status

### Response Format

Gate results are included in transition/claim responses:

```json
{
  "gate": {
    "gate_name": "Definition of Ready",
    "policy": "warn",
    "passed": false,
    "criteria": [
      {"text": "Effort estimated", "passed": true, "type": "checker"},
      {"text": "Problem statement clear", "passed": true, "type": "judgment"},
      {"text": "Not oversized", "passed": false, "type": "checker",
       "message": "Item effort is XL — consider decomposing"}
    ]
  }
}
```

## Consequences

- Agents receive structured quality guidance at workflow boundaries
- Gate criteria are discoverable and configurable per-KB
- The `warn` default avoids blocking workflows while still surfacing quality signals
- Existing rubric checkers are reused for automated criteria
- Future grooming agents can use the same DoR checklist to prepare items
