---
id: worktree-no-lost-commits-invariant
type: backlog_item
title: "Worktree collaboration: pin the no-lost-commits invariant across merge/reject/reset paths"
kind: tech_debt
status: proposed
priority: medium
effort: S
created: "2026-07-04"
tags: [worktree, collaboration, git, testing, trust]
links:
- target: adr-0029
  relation: implements
  kb: pyrite
---

## Problem

ADR-0024's conflict path says: "If the rebase fails (conflict), the
worktree is reset to main and the user is notified." A worktree
reset is safe ONLY if the user's branch ref (and therefore their
commits) survives — git keeps commits reachable from refs; a reset
that drops or force-moves `user/{name}` without preserving the old
tip makes user work unrecoverable. For invited peers, silently
losing submitted-but-unmerged (or post-submit) edits is a
first-order trust violation — worse than any bug the pilot could
surface.

Not verified either way — WorktreeService.merge/reject/
reset_to_main (worktree_service.py:318-418) need reading with this
question, and the invariant needs a test regardless of the answer.

## Fix

1. Read the merge/reject/reset paths; where a reset would orphan
   commits, preserve the old tip first (e.g. move it to
   `user/{name}/archive-{timestamp}` or a tag) before resetting.
2. Tests pinning the invariant: after each of (a) successful merge +
   rebase, (b) merge with rebase conflict → reset, (c) reject, (d)
   reset_to_main with unsubmitted edits, (e) delete_worktree — every
   commit the user ever made is still reachable from some ref
   (`git rev-list --all` contains them). Fault-inject the conflict
   case with genuinely conflicting edits.
3. Surface the recovery affordance: when a reset preserves an
   archive ref, the user-facing notification names it ("your edits
   are preserved at ...") per [[in-band-degradation-signaling]].

## Scope note

Post-0.25 (the pilot is read-only; worktree writes aren't active for
peers). Belongs to the write-phase gate set in ADR-0029 §6. Filed
now because the invariant is cheap to pin while the review-flow code
is fresh.

## Acceptance criteria

- The five-path test above passes; the conflict case fails on any
  implementation that orphans commits.
