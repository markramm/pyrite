---
id: feat-relaxed-state-machine-mode-open-but-logged-any-transition-with-required-reason
type: backlog_item
title: "FEATURE PROPOSAL (Mark direction 2026-06-10, from investigation-conductor session)"
kind: feature
status: proposed
priority: high
effort: S
tags: [bug, conductor-filed, cli, task-system]
rank: 1175
---

FEATURE PROPOSAL (Mark direction 2026-06-10, from investigation-conductor session). Add a RELAXED state-machine MODE rather than removing the machine. Separate two checks the machine currently conflates: (1) is 'status' a member of the allowed STATE SET — always enforce (cheap; catches typos; keeps index queryable); (2) is this TRANSITION legal given current state — make OPTIONAL.

Config: task_state_machine: { states: [open,claimed,in_progress,review,blocked,done,failed], enforce_transitions: false, require_reason_on_transition: true }. Rule: any status change allowed iff status_reason (+status_by) is set; git supplies who/when/ordered-history.

THE ONE INVARIANT TO KEEP: open->claimed stays an ATOMIC compare-and-swap (the only concurrency collision point + the crash-recovery breadcrumb). It's a concurrency guard, not a lifecycle rule, so it lives OUTSIDE the transition table and stays guarded in BOTH modes. Mark: 'Claimed is atomic. Generally there is no contention on the ticket after that as the agent works it to completion (or times out).'

MOTIVATION (friction observed every conductor tick): (a) conductor cannot triage an UNCLAIMED task open->blocked (no orchestrator-grooming path that skips the claim) — currently worked around with parked_awaiting frontmatter + hand-edits; (b) subsumes issue-add-held-state — no 'held' enum needed: status:blocked + status_reason:'deliverables-met, awaiting GAO docket' is more expressive than any fixed state; (c) reason-on-EVERY-transition, uniform, no happy-path exemption (exempting 'obvious' transitions smuggles a mini transition-table back in). REASON enforced by rejecting the write, not by convention. Reason field is what makes a git diff legible weeks later. CAVEAT: a free status can drift from reality (done with no artifact) — but the strict machine never guarded transition TRUTH either, only ORDER; the real guard is the consumer's QC pass. Owner: pyrite repo. Related: issue-add-held-state-to-pyrite-task-state-machine (this subsumes it).

## PO triage note (2026-06-10)

Ranked into **Tier A meta-bugs** (rank 1175) per PO call. The conductor
explicitly notes friction "every conductor tick" because it can't triage
unclaimed tasks `open→blocked` without a workaround. That's the same
"grooming-tools-sabotage-grooming" family as the rank-projection,
prioritize-clobbers-ranks, and index-sync-after-update bugs in this tier.

The relaxed mode is itself a grooming-quality improvement: it removes
the hand-edit/`parked_awaiting` workaround that conductor sessions are
currently using to express states the strict machine doesn't allow.

Subsumes the proposed `issue-add-held-state-to-pyrite-task-state-machine`
(per the ticket body), which can be retired in the same commit that
implements the relaxed mode.

