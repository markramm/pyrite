---
id: notifications-condition-ledger
type: design_doc
title: "Notifications as a Condition Ledger — system warnings across CLI, MCP, and web (Phase 1+, post-0.25)"
status: draft
author: markr
date: "2026-07-03"
reviewers: []
tags: [notifications, warnings, agent-dx, web, cli, mcp, design, async]
---

# Notifications as a Condition Ledger

**Scope note:** Phase 0 (the `warnings` array, stderr lines, static
sidebar chip) ships under [[in-band-degradation-signaling]] and is
0.25 work. Everything else here is Phase 1+ — captured now so the
conditions work has a design when it gets scheduled. Operator
framing: "the more async interactions that exist in the system the
more we need some kind of notifications"; MCP/CLI/GUI must provide
the same core features in context-appropriate forms.

## The model: conditions, not an inbox

Pyrite's problems are mostly **states, not events** — "index stale
for cascade-research", "plugin skipped for this KB", "3 entries
failed to parse", "embedding backlog: 412". A bell-and-feed inbox
handles states badly in both directions: the feed item scrolls away
while the condition persists, or the condition self-heals and the
stale feed item lies.

So: a **condition ledger, derived from system state** — the same
move the product makes everywhere (files/git are truth, index is
derived; here system state is truth, notifications are derived). A
condition:

```yaml
code: INDEX_STALE          # mono, shared vocabulary with error contract
severity: warning          # critical | warning | info — semantic axis
scope: cascade-research    # KB name or "system"
message: "Search may miss entries newer than Jul 1."
suggestion: "pyrite index sync -k cascade-research"
first_seen: 2026-07-01T…   # coalescing key: (code, scope)
last_seen: …
count: 214                 # occurrences since first_seen
status: active             # active | acknowledged | resolved
kind: check                # check | task (tasks carry progress)
```

Deliberately the same field vocabulary as `pyrite/utils/errors.py`
and the Phase-0 `warnings` array — a notification IS a warning that
outlived its request.

**Three structural consequences:**

1. **Coalescing is structural.** Same warning on 200 searches = one
   condition, `count: 200`. Key: `(code, scope)`.
2. **Conditions self-resolve.** Reindex clears INDEX_STALE; the
   ledger moves it to "recently resolved" with no user action. There
   is NO mark-as-read — read-state isn't truth, system state is. The
   only user verb is **acknowledge** (mute; re-alert on worsen or
   change; never delete). An acknowledged condition that worsens
   un-acknowledges itself.
3. **Async jobs are the same object** — `kind: task` with progress,
   resolving on completion. Notifications + job tracking are ONE
   "system activity" surface; do not build a second system for jobs
   later.

**Anti-drift rule (the one thing to preserve if all else changes):
derive, coalesce, self-resolve.** A stored inbox humans must groom is
the dual-registry bug rebuilt in the UX layer — a second source of
truth drifting from the system it describes. The store may cache,
but a re-check must always be able to reconstruct it.

## The signature: one status line, the same sentence everywhere

No bell, anywhere. A bell promises messages from people; these are
**instrument readings**. The persistent affordance is a status line
in the utility face (JetBrains Mono) whose string is IDENTICAL
across surfaces:

```
● all checks pass · 2 jobs idle        ▲ 2 warnings · 1 kb affected
```

- CLI: the summary line of `pyrite status`.
- Web: that exact string, mono + semantic dot, in the sidebar footer
  (beside the existing `v0.9 · synced` affordance); click opens the
  panel.
- MCP: `status_line` field on `kb_orient` (+ structured array).

Cross-surface parity made visible rather than claimed.

## Per-surface design

### CLI — `pyrite status` (the git-status of knowledge-as-code)

```
$ pyrite status
▲ 2 warnings

  ▲ INDEX_STALE        cascade-research     first seen 2d ago · ×214
    Search may miss entries newer than Jul 1.
    → pyrite index sync -k cascade-research

  ▲ PLUGIN_SKIPPED     journalists          first seen 4h ago · ×3
    KB-type check failed; journalism-investigation is disabled here.
    → pyrite plugin doctor journalism-investigation

  ⟳ embedding backlog  412 remaining        ~3m at current rate

recently resolved (7d): ✓ PARSE_DROPPED boyd — cleared Jul 2 by reindex
```

Verbs: `pyrite status [--json]`, `status ack <code> [-k kb]`,
`status check <code>` (re-run the probe). Plus the Phase-0 trailer:
any command touching an affected KB appends one stderr line —
`▲ 2 active conditions affect this KB · pyrite status` — so agents
that never ask still get told in-band.

### MCP — three touchpoints, no new ceremony

1. `warnings` array on every tool result (Phase 0, transient).
2. `kb_orient` LEADS with active conditions — a cold agent's first
   call carries "search on X may be stale" before it trusts a search.
3. `kb_status` tool mirroring the CLI verbs. Same codes, fields,
   suggestions on all surfaces.

### Web — ledger line → System activity panel; toasts demoted

```
┌ sidebar ──────────┐        ┌ System activity ────────────────────────┐
│ …nav…             │        │ ACTIVE                                  │
│                   │        │ ▌▲ Index behind — cascade-research      │
│                   │        │ ▌  Search may miss entries after Jul 1. │
│                   │        │ ▌  [Reindex now]   2d · ×214 · ack      │
│                   │        │ ▌▲ Plugin disabled for this KB          │
│───────────────────│        │ ▌  [Run check]     4h · ×3   · ack      │
│ v0.9 · synced     │        │ RUNNING                                 │
│ ▲ 2 warnings    ◂─┼─click  │ ⟳ Embedding backlog  ▓▓▓▓░░  412 left   │
└───────────────────┘        │ RECENTLY RESOLVED                       │
                             │ ✓ 3 entries reindexed — boyd · Jul 2    │
                             └─────────────────────────────────────────┘
```

- Each condition: 2px severity left-border — deliberately the SAME
  visual grammar as the epistemic callout in entries
  ([[web-design-system-spec]] §4b): a left-bordered block means
  "trust this less; here's why", for content and chrome alike.
- Severity on the semantic axis only; never brand gold.
- The suggestion renders as a **button that performs the
  remediation** ("Reindex now"), not advice about it.
- "Recently resolved" stays visible (dimmed, 7 days) — watching
  conditions clear themselves is how the panel earns trust.

**Toast policy (the anti-noise constitution):** critical → toast
once + ledger; warning → ledger only; job completion → toast only if
you started the job this session. A condition toasts at most once
per appearance; recurrence increments the count silently.

## Copy rules

Effect first, cause second, action last ("Search may miss entries
newer than Jul 1" before any mention of mtimes). Codes stay mono and
visible — agents and humans share vocabulary; a pilot peer can paste
`INDEX_STALE` into a bug report. No apologies, no "Oops", warnings
are not red. "Acknowledge" is the verb on every surface.

## Feature parity matrix

| Verb | CLI | MCP | Web |
|---|---|---|---|
| Summary line | `pyrite status` line 1 | `kb_orient.status_line` | Sidebar footer chip |
| List/inspect | `pyrite status [--json]` | `kb_status` | System activity panel |
| Acknowledge | `status ack <code>` | `kb_status` ack | "ack" on the row |
| Re-check | `status check <code>` | `kb_status` check | [Run check] button |
| Remediate | suggestion string | suggestion string | action button runs it |
| In-band per-op | stderr trailer + warnings[] | warnings[] on result | toast (per policy) |

## Phasing

- **Phase 0 (0.25, ticketed):** [[in-band-degradation-signaling]] —
  warnings array + stderr + static sidebar chip from `index health`.
- **Phase 1:** conditions store (persist + coalesce warnings that
  outlive a request; reconstructable from checks), `pyrite status`
  verbs, System activity panel, `kb_status` + orient integration.
- **Phase 2:** jobs-as-conditions with progress, remediation action
  buttons, event subscriptions if the fleet wants push.

## Related

[[in-band-degradation-signaling]] (Phase 0),
[[web-design-system-spec]] (tokens, epistemic-callout grammar),
[[docs-operational-contracts-travel-with-tool]] (agents must learn
to check warnings/status), [[plugin-type-resolution-scoping]]
(PLUGIN_SKIPPED producer), [[verify-after-write-on-the-index-path]]
and [[collapse-kb-registry-to-one-source-of-truth]] (producers of
the index/registry condition family), event-bus-webhooks (Phase 2
transport candidate).
