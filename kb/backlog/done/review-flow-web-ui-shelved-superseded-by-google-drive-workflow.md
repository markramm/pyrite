---
id: review-flow-web-ui-shelved-superseded-by-google-drive-workflow
title: "Review-flow web UI shelved — editor workflow superseded by Google Drive; in-Pyrite edit feature still wanted, not urgent"
type: backlog_item
tags: [web-ui, review, editing, deferred, superseded-workflow, worktree]
importance: 5
kind: feature
status: done
priority: medium
effort: M
rank: 2350
---

## Update 2026-07-03: shipped, not shelved

The stashed WIP described below was applied and committed in `26b3c9a`
("feat(web): add entry comments panel and submit-for-review flow") —
all 9 files (5 modified, 4 new) match exactly. `git stash list` no
longer contains this work; it is live on `dev`.

This ticket's original framing (Amy's workflow moved to Google Drive,
so the in-Pyrite review UI is descoped) may or may not still be the
operating decision — a different session shipped the feature without
updating this ticket, so the intent behind that commit is not captured
here. Whoever owns that work should confirm: is this now a supported,
general-purpose "Edit entry" feature (per the "What's still wanted"
section below), or should it be reverted/gated behind a flag pending
the Google Drive workflow decision?

Marking `done` so the backlog does not claim the feature does not
exist when `web/src/routes/review/` is live on `dev`. Re-open or split
into a follow-up ticket if the Amy-specific framing still needs
reconciling with what shipped.

---

## Original context (2026-06-09)

A review-flow web UI was in flight to support Amy's editorial workflow:
non-admin editor opens a draft, makes inline edits, adds comments
anchored to text ranges, submits, and an admin merges through the
worktree collaboration system. The backend integration shipped and is
covered by an e2e test (tests/test_review_flow_e2e.py, committed
2026-06-05 in 8cdd0b8).

On 2026-06-09, Amy's workflow moved to Google Workspace instead:

1. Pyrite (or a script) auto-creates a Google Doc in a shared Drive from
   the draft.
2. Amy edits and revises in Google Docs — familiar tooling, native comment
   thread, no Pyrite-UI learning curve.
3. The author finds an image while she edits, then paste-publishes the
   final version to Substack from the Doc.

The Google Drive flow fits her workflow better than an inline-editor
surface in Pyrite would. The review-flow web UI work was therefore
descoped at the time — not deleted, but no longer urgent. (Superseded
by the 2026-07-03 update above: it shipped anyway.)

## What was stashed (now applied, see update above)

Modified (5):
- web/src/lib/api/types.ts
- web/src/lib/components/layout/Sidebar.svelte
- web/src/lib/stores/entries.svelte.ts
- web/src/lib/stores/ui.svelte.ts
- web/src/routes/entries/[id]/+page.svelte

New (4):
- web/src/lib/components/entry/CommentsPanel.svelte
- web/src/lib/components/entry/SubmitForReview.svelte
- web/src/lib/editor/comment-anchor.ts
- web/src/routes/review/ (route directory)

The backend integration remains live:
- WorktreeService (commit 9e13966 — two fixes)
- KBService.update_entry metadata-merge (d0e2677)
- Endpoint metadata wire-through (d0e2677)
- E2E test (tests/test_review_flow_e2e.py) — passes; covers the
  worktree → submit → merge → KB contract for any editor flow (Amy or
  otherwise), not specifically the Pyrite-UI flavor.

## What's still wanted (if reconciling as a general feature)

A general in-Pyrite edit feature for entries (not specifically the Amy
draft-review use case) — for ad-hoc edits by any user who would rather
stay in the Pyrite web UI than round-trip through Google Drive. If the
shipped work is meant to serve this, consider:

- The comment-anchoring approach (web/src/lib/editor/comment-anchor.ts)
  was tailored to the Amy use case (anchoring to specific paragraph
  ranges). A general edit feature may want a different model.
- The submit-for-review flow assumes the worktree path (right per
  ADR-0024 for multi-user editing), but "Submit for Review" framing may
  need rewording if this is now general-purpose rather than
  Amy-specific.

## Related

- tests/test_review_flow_e2e.py — e2e test; covers the backend
  worktree → KB contract.
- Commit 26b3c9a — the stashed WIP applied and shipped (2026-07-02/03).
- Commit d0e2677 — metadata-merge + REST wiring (both bugs found
  during this WIP).
- Commit 9e13966 — two worktree-bootstrap bugs (both fixed during
  this WIP).
- Commit 8cdd0b8 — where the e2e test accidentally landed in a loop
  commit; left in place because it tests real infrastructure.
- ADR-0024 — worktree collaboration model.
- epic-fork-system (done at 3/8) — the multi-user editing
  infrastructure this WIP was building on.

