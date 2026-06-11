---
id: feat-relaxed-state-machine-mode-open-but-logged-any-transition-with-required-reason
title: "FEATURE PROPOSAL (Mark direction 2026-06-10, from investigation-conductor session)"
type: backlog_item
tags: [bug, conductor-filed, cli, task-system]
importance: 5
kind: feature
status: proposed
priority: high
effort: S
rank: 1175
---

FEATURE PROPOSAL (Mark direction 2026-06-10, from investigation-conductor session). Add a RELAXED state-machine MODE rather than removing the machine. Separate two checks the machine currently conflates: (1) is 'status' a member of the allowed STATE SET — always enforce (cheap; catches typos; keeps index queryable); (2) is this TRANSITION legal given current state — make OPTIONAL.

Config: task_state_machine: { states: [open,claimed,in_progress,review,blocked,done,failed], enforce_transitions: false, require_reason_on_transition: true }. Rule: any status change allowed iff status_reason (+status_by) is set; git supplies who/when/ordered-history.

THE ONE INVARIANT TO KEEP: open->claimed stays an ATOMIC compare-and-swap (the only concurrency collision point + the crash-recovery breadcrumb). It's a concurrency guard, not a lifecycle rule, so it lives OUTSIDE the transition table and stays guarded in BOTH modes. Mark: 'Claimed is atomic. Generally there is no contention on the ticket after that as the agent works it to completion (or times out).'

MOTIVATION (friction observed every conductor tick): (a) conductor cannot triage an UNCLAIMED task open->blocked (no orchestrator-grooming path that skips the claim) — currently worked around with parked_awaiting frontmatter + hand-edits; (b) subsumes issue-add-held-state — no 'held' enum needed: status:blocked + status_reason:'deliverables-met, awaiting GAO docket' is more expressive than any fixed state; (c) reason-on-EVERY-transition, uniform, no happy-path exemption (exempting 'obvious' transitions smuggles a mini transition-table back in). REASON enforced by rejecting the write, not by convention. Reason field is what makes a git diff legible weeks later. CAVEAT: a free status can drift from reality (done with no artifact) — but the strict machine never guarded transition TRUTH either, only ORDER; the real guard is the consumer's QC pass. Owner: pyrite repo. Related: issue-add-held-state-to-pyrite-task-state-machine (this subsumes it).

## PO triage note (2026-06-10)

Ranked into **Tier A meta-bugs** (rank 1175) per PO call. The conductor explicitly notes friction "every conductor tick" because it can't triage unclaimed tasks open->blocked without a workaround. That's the same "grooming-tools-sabotage-grooming" family as the rank-projection, prioritize-clobbers-ranks, and index-sync-after-update bugs in this tier.

The relaxed mode is itself a grooming-quality improvement: it removes the hand-edit/parked_awaiting workaround that conductor sessions are currently using to express states the strict machine doesn't allow.

Subsumes the proposed issue-add-held-state-to-pyrite-task-state-machine (per the ticket body), which can be retired in the same commit that implements the relaxed mode.

## Design questions (yielded from /pyrite-dev cron fire 2026-06-11)

Before implementation, the following decisions need to be locked. The ticket gestures at answers but a fire that picks this up needs them nailed down to write GREEN code without speculation:

1. **Config location.** enforce_transitions / require_reason_on_transition — per-KB config (kb.yaml schema), global Pyrite settings, or task-system-specific (e.g., pyrite/models/task.py constant overridable via env)? **Recommendation: per-KB**, since some KBs (investigations) want relaxed, others (CI/release pipelines) want strict. Confirm?

2. **Field shape.** status_reason (free string, required ≥ N chars?) and status_by (auto-fill from PluginContext.user_id or require explicit?). **Recommendation: free string, min 3 chars, status_by auto-filled from context when available, falls back to required CLI flag.** Confirm?

3. **Toggle granularity.** Per-call CLI flag (pyrite task update --force), per-KB config (relaxed for whole KB), or both? **Recommendation: per-KB config sets the default; no per-call override (keeps git diffs auditable — operators can't quietly bypass).** Confirm?

4. **Backward-compat.** Existing tasks have no status_reason field. Three options:
   - (a) Fail closed: any future update to such a task requires reason on EVERY transition (relaxed mode rule).
   - (b) Fail open: existing tasks grandfathered; new fields required only for tasks created after a flag is set.
   - (c) Migration script: one-off backfill of status_reason='pre-relaxed-mode'.

   **Recommendation: (a) fail closed.** Cleanest semantics, no migration debt; the next update auto-backfills via the required field. Confirm?

5. **CLI ergonomics.** pyrite task update <id> -f status=blocked --reason "awaiting GAO"? Or position-required pyrite task update <id> blocked "awaiting GAO"? **Recommendation: --reason flag + accept --status-reason alias** to match frontmatter field name. Confirm?

6. **Atomic claim.** Verify: open->claimed is currently atomic via a CAS-equivalent in the task service? If implemented via filesystem rename or DB row update, relaxed mode must NOT touch this path. Need to read pyrite/services/task_service.py to confirm.

7. **Retire-in-same-commit.** Confirm: when this lands, also delete issue-add-held-state-to-pyrite-task-state-machine (status: wont_do, note: subsumed by relaxed mode) per ticket body. Need to verify the ticket still exists.

If recommendations are accepted as-written, the next fire can go straight to RED tests + implementation. Estimate: ~2 fires for code + tests, 1 fire for CLI surface + docs.
