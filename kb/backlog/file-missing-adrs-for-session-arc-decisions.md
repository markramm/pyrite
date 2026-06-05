---
id: file-missing-adrs-for-session-arc-decisions
type: backlog_item
title: "File three missing ADRs: central PyriteError handler, index-health drift checks, status-enum reconciliation"
kind: documentation
status: proposed
priority: medium
effort: S
tags: [adr, documentation, architecture, error-handling, schema-validation]
---

## Problem

Three major architectural decisions shipped during the recent session arc
without ADRs. Future contributors will re-litigate them or unwind them by
accident — exactly what ADRs exist to prevent. The documentation audit caught
all three.

The decisions are real (load-bearing, opinionated) and irreversible without
breakage:

### 1. Central `PyriteError` handler (REST)

Commit `c348087` added `register_pyrite_exception_handler()` in
`pyrite/server/api.py`, mapping the typed exception hierarchy to HTTP status
codes through a single FastAPI exception handler. Replaces the ad-hoc
`raise HTTPException(detail={...})` pattern that was scattered across
endpoints. Decision points worth recording:

- Status code mapping (e.g. `KBNotFoundError -> 404`, `KBReadOnlyError -> 403`,
  `ValidationError -> 422`, `FrontmatterError -> 422`, etc.)
- The uniform `{"code", "message"}` body shape
- Why `auth_service` was deliberately excluded from the typed-exception sweep
- The two-response-shape situation this creates (central-handler shape vs
  endpoint-level `HTTPException(detail={...})` — partially superseding,
  partially coexisting)

### 2. Index-health drift-check pattern

Commits `f499e60`, `1f15fae`, and earlier shipped four drift checks in
`IndexManager.check_health()`: undeclared types, missing required fields,
malformed frontmatter, invalid statuses. The decision pattern (validate at
index time without blocking, surface as health warnings, plugin validators
do the actual checking) is now the de-facto pattern for any future drift
detection. Worth recording so the next "should this be a validator, a hook,
or a health check?" question has a documented answer.

### 3. Status enum reconciliation (`completed` -> `done`, add `superseded`)

Commit `402f0a4` normalized 75 items from `completed` to `done`, and `1f15fae`
added `superseded` to `BACKLOG_STATUSES`. The vocabulary decision is now
load-bearing — the dual-vocab bug it cleaned up was corrupting epic rollup
math, and the new `invalid_statuses` health check enforces the canonical
vocabulary. The decision worth recording is *why* the kb.yaml-declared
canonical vocabulary takes precedence over the legacy variants, and how the
status-enum-at-index-time enforcement closes the loop.

## Solution

File three ADRs:

- **ADR-0027 — Central PyriteError exception handler** (REST layer).
  Status: accepted. Decision text references commit `c348087`. Includes the
  full status-code mapping table and the explicit list of typed exceptions
  the handler routes.
- **ADR-0028 — Index-health drift-check pattern.** Status: accepted. Records
  the "validate at index time, surface as health warning, plugin validators
  do the checking" pattern. References `enforce-backlog-status-enum-at-index-time`
  ticket and the four landed checks.
- **ADR-0029 — Status vocabulary reconciliation.** Status: accepted. Records
  the `completed` -> `done` rename, the `superseded` addition, and the
  enforcement-at-index-time decision. References commits `402f0a4` and
  `1f15fae`.

Use the `pyrite sw new-adr` command for all three so they get the right
frontmatter and numbering automatically.

## Acceptance criteria

- Three ADR files created in `kb/adrs/` with proper frontmatter and `accepted`
  status.
- Each ADR has Context, Decision, and Consequences sections per the existing
  ADR pattern (sample: ADR-0008, ADR-0013).
- Each ADR references the commit(s) implementing it.
- ADR-0027 has the full status-code mapping table.
- ADR-0028 explains when to use a health check vs a hook vs a validator
  (the three "where does this check live?" options).
- ADR-0029 records why the kb.yaml vocabulary wins and what
  `invalid_statuses` enforces.

## Out of scope

- The ADR-0022 filename out-of-sequence issue (different ticket if filed).
- The README + runbook references to non-existent `extensions/task` (separate
  cleanup).

## Related

- [[enforce-backlog-status-enum-at-index-time]] — implementing ticket for
  ADR-0029's decision.
- ADR-0002 — the plugin-validator invocation pattern ADR-0028 builds on.
- ADR-0013 (Unified Database Connection) — adjacent architectural ADR;
  similar level of formality expected.
- The doc audit findings committed alongside this ticket.
