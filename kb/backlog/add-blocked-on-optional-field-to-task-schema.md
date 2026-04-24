---
id: add-blocked-on-optional-field-to-task-schema
type: backlog_item
title: "Add optional `blocked_on` list field to task schema with prefix-based blocker taxonomy"
kind: feature
status: proposed
priority: medium
effort: S
tags: [task-system, schema, cascade-research, investigation-workflow, foia, orchestration]
---

## Problem

Tasks that are deliverable-complete but whose core research question depends on an
external resource (FOIA response, interactive-session database, next scheduled
filing, civil-discovery window, a named person) have no good home in the current
`open | in_progress | blocked | done` state machine.

The cascade-research investigation conductor (2026-04-23 ticks 2–4) hit this
repeatedly:

- `task-inv1-kvg-bonding-surety` — KVG org profile created, $113M contract
  identifier extracted, bonding architecture mapped. Core question (surety
  issuer, FAR waiver, contracting officer) requires SAM.gov authenticated session
  OR FOIA to ICE OAQ 70CDCR and NAVSUP Mechanicsburg.
- `task-inv3-ags-client-list` — AGS org profile 4x expanded, four strategic
  partnerships documented, confirmed AGS files no FARA / no LDA by design. Core
  question (client list) requires FARA interactive search + Checkmate LDA
  quarterly-filing review + FOIA to Treasury/State.
- `task-inv4-1789-capital-lp-roster` — Form ADV + Form D roster committed,
  $861M–$2B capital-raise aggregate timeline documented. Core question (named
  sovereign-wealth-fund LPs) requires feeder-fund documents + next ADV
  amendment (mid-2026) + Ballhaus WSJ FOIA response.
- `task-inv4-tahnoon-500m-corporate-vehicles` — Aryam Investment 1 twin-shell
  structure identified, three G42 executives named. Core question (second
  tranche allocation, CFIUS/FinCEN, on-chain forensics) requires Delaware
  interactive + ADGM interactive + Etherscan analysis + WSJ direct outreach.

In the current state machine, "deliverable-complete but core-question-gated"
collapses to either `blocked` (loses completed-deliverable status) or `done`
(loses visibility of the research gap). The conductor workaround is creating
priority-6 `human-gated-` prefixed follow-on tasks — workable but:

1. No structured query like "show everything blocked on FOIA to ICE OAQ" — one
   FOIA to a single agency would unblock ~4 tasks simultaneously but there's
   no way to see that leverage without manual scanning.
2. `in_progress` + external-event-waiting is a different state from
   `in_progress` + worker-actively-executing — the conductor can't distinguish
   without reading every work log.
3. The `human-gated-` prefix in task IDs drifts (capitalization, phrasing) and
   doesn't aggregate across kbs.

## Existing `dependencies` field — what this is NOT duplicating

Pyrite already has a working task-to-task dependency mechanism: `dependencies:
list[str]` on the task frontmatter holds child-task IDs, the task enters
`blocked` status until all deps resolve to `done`, and `task_service` provides
`get_blocked_by()`, `unblock_ready_tasks()`, and critical-path analysis.
`pyrite task status` displays "Dependencies: ..." inline.

This ticket does NOT propose changing `dependencies`. It proposes a parallel
field for blockers that are NOT other tasks.

## Proposed change

Add an optional `blocked_on` field to the task frontmatter for NON-TASK
blockers (external events the task system cannot model as sibling tasks). List
of structured strings with convention-based prefixes:

```yaml
blocked_on:
  - "foia:ice-oaq-70cdcr"
  - "foia:navsup-mechanicsburg"
  - "interactive:sam-gov"
  - "interactive:fara-efile"
  - "interactive:lda-disclosures-house-gov"
  - "date:2026-08-01"               # Form ADV annual amendment expected
  - "person:mark"                    # human required, no external gate
  - "event:wsj-ballhaus-foia-response"
  - "litigation:maryland-injunction-discovery"
```

Task-to-task blockers continue to use `dependencies:` — the `task:` prefix is
NOT introduced here because `dependencies:` already handles it and the auto-
unblock behavior is valuable.

The field is orthogonal to `status`. A task can be `in_progress` and
`blocked_on` a specific external event — it's not dead, it's waiting for one
thing. A task can be `done` and still have `blocked_on` populated to capture
the follow-up surface for a future reopening.

### CLI

```
pyrite task list --kb cascade-research --blocked-on 'foia:*'
pyrite task list --kb cascade-research --blocked-on 'date:<=2026-06-01'
pyrite task list --kb cascade-research --blocked-on 'interactive:sam-gov'
pyrite task update <task-id> --add-blocker 'foia:ice-oaq-70cdcr'
pyrite task update <task-id> --remove-blocker 'foia:ice-oaq-70cdcr'
```

### Prefix convention (initial; free-form strings otherwise)

| Prefix | Semantics | Example |
|---|---|---|
| `foia:` | FOIA request to a specific agency | `foia:ice-oaq-70cdcr` |
| `interactive:` | Interactive-session database | `interactive:fara-efile` |
| `date:` | Wait until this date (ISO-8601) | `date:2026-08-01` |
| `event:` | Waiting on a specific external event | `event:next-form-adv-amendment` |
| `person:` | Blocked on a specific human | `person:mark` |
| `litigation:` | Gated by a civil-discovery process | `litigation:maryland-injunction` |
| `paywall:` | Gated by a specific paywall | `paywall:stat-news` |

Deliberately NOT in the prefix list: `task:`. Task-to-task dependencies are
handled by the existing `dependencies:` field which provides auto-unblock
semantics this field does not.

Unknown prefixes accepted; drift is tolerated at first (cleanup via conductor
QC pass). If drift becomes painful, promote common values to a controlled
vocab in kb.yaml.

## Acceptance criteria

- [ ] Task frontmatter accepts optional `blocked_on: list[string]`
- [ ] `pyrite task create --blocked-on <value>` (repeatable) at creation time
- [ ] `pyrite task update --add-blocker <value>` / `--remove-blocker <value>`
- [ ] `pyrite task list --blocked-on <glob-or-prefix>` filter
- [ ] `pyrite task status <id>` displays blockers in entry detail
- [ ] Blockers propagate to search (ripgrep frontmatter filter at minimum)
- [ ] `blocked_on` is orthogonal to `status` (tasks in any status may carry it)
- [ ] Migration: no-op for existing tasks (field is optional)

## Out of scope for initial change

- No automatic state transitions based on `blocked_on` values
- No calendar integration for `date:` prefix blockers
- No GitHub issue linking for `foia:` / `litigation:` prefixes
- No auto-unblock when an event-prefix string appears in another task's completion

These can follow as separate tickets once usage patterns stabilize.

## Related context

- Current conductor workaround documented in
  `cascade-research/notes/task-*.md` work logs for tasks completed 2026-04-23
- Conductor applies a `human-gated-` task-ID prefix as the current workaround
- Investigation map `themes/investigation-map-april-2026.md` ("Convergent
  Agent-Unsolvable Blockers" entry under Cross-Investigation Research
  Priorities) documents the leverage available if blockers are queryable:
  one FOIA/discovery project could unblock ~24 documented gaps simultaneously

## Rationale — why not a new status value

The alternative design — add a `human-required` status value — was considered
and rejected. A single status value collapses heterogeneous blockers (FOIA
agency, interactive database, date-waited, named person) into one bucket that
doesn't support the core workflow query: "which tasks share a blocker, and
therefore unblock together when the blocker resolves?"

A list field with prefix conventions preserves status orthogonality, scales
to multi-blocker tasks (the KVG bonding task has both SAM.gov interactive AND
two separate FOIA agencies), and enables the targeted queries that make
backlog grooming useful.
