---
id: review-flow-web-ui-shelved-superseded-by-google-drive-workflow
type: backlog_item
title: "Review-flow web UI shelved — editor workflow superseded by Google Drive; in-Pyrite edit feature still wanted, not urgent"
kind: feature
status: deferred
priority: medium
effort: M
tags: [web-ui, review, editing, deferred, superseded-workflow, worktree]
rank: 2350
---

## Context

A review-flow web UI was in flight to support Amy's editorial workflow:
non-admin editor opens a draft → inline edits → comments anchored to text
ranges → submits → admin merges through the worktree collaboration system.
The backend integration shipped and is covered by an e2e test
(`tests/test_review_flow_e2e.py`, committed 2026-06-05 in `8cdd0b8`).

On 2026-06-09, Amy's workflow moved to **Google Workspace** instead:

1. Pyrite (or a script) auto-creates a Google Doc in a shared Drive from
   the draft.
2. Amy edits and revises in Google Docs — familiar tooling, native comment
   thread, no Pyrite-UI learning curve.
3. The author finds an image while she edits, then paste-publishes the
   final version to Substack from the Doc.

The Google Drive flow fits her workflow better than an inline-editor surface
in Pyrite would. The review-flow web UI work is therefore **descoped** —
not deleted, but no longer urgent.

## Current state of the WIP

**Stashed** at `stash@{0}` on 2026-06-09 with message referencing this
ticket. 9 files total:

Modified (5):
- `web/src/lib/api/types.ts`
- `web/src/lib/components/layout/Sidebar.svelte`
- `web/src/lib/stores/entries.svelte.ts`
- `web/src/lib/stores/ui.svelte.ts`
- `web/src/routes/entries/[id]/+page.svelte`

New (4):
- `web/src/lib/components/entry/CommentsPanel.svelte`
- `web/src/lib/components/entry/SubmitForReview.svelte`
- `web/src/lib/editor/comment-anchor.ts`
- `web/src/routes/review/` (route directory)

The **backend** integration is NOT stashed and remains live:
- `WorktreeService` (commit `9e13966` — two fixes)
- `KBService.update_entry` metadata-merge (`d0e2677`)
- Endpoint `metadata` wire-through (`d0e2677`)
- E2E test (`tests/test_review_flow_e2e.py`) — passes; covers the
  worktree → submit → merge → KB contract for ANY editor flow (Amy or
  otherwise), not specifically the Pyrite-UI flavor. Keep.

## What's still wanted

A general in-Pyrite edit feature for entries (not specifically the Amy
draft-review use case) remains valuable — for ad-hoc edits by any user
who'd rather stay in the Pyrite web UI than round-trip through Google
Drive. The stashed work is a reasonable starting point if/when that
priority moves up.

## Recovery instructions (when this is picked up)

```bash
git stash list                # confirm stash@{0} is the review-flow WIP
git stash show -p stash@{0}   # review the diff before applying
git stash apply stash@{0}     # apply without dropping
# OR
git stash pop stash@{0}       # apply and drop
```

Before resuming, consider:

- The 4-week gap means web/ dependencies may have moved. Run
  `cd web && npm install && npm run build` to catch breaks.
- The comment-anchoring approach (`web/src/lib/editor/comment-anchor.ts`)
  was tailored to the Amy use case (anchoring to specific paragraph
  ranges). A general edit feature may want a different model.
- The submit-for-review flow assumed the worktree path. For non-Amy
  users this is still right (it's how multi-user editing works per
  ADR-0024), but the UI affordances ("Submit for Review" button) may
  need rewording for general use.

## Acceptance criteria (when revived)

- The stash applies cleanly against current `dev` (or document the
  rebase work needed).
- The web UI offers an "Edit entry" affordance from the entry detail
  view.
- The edit posts through the existing worktree write-routing
  (`worktree-write-routing` ticket, done) so the contract with the
  e2e test holds.
- A general-purpose name replaces "review" / "Submit for Review"
  framing — the Amy-specific framing assumed an editorial workflow
  that no longer applies.

## Related

- `tests/test_review_flow_e2e.py` — e2e test that survived; covers the
  backend worktree → KB contract.
- Commit `d0e2677` — metadata-merge + REST wiring (both bugs found
  during this WIP).
- Commit `9e13966` — two worktree-bootstrap bugs (both fixed during
  this WIP).
- Commit `8cdd0b8` — where the e2e test accidentally landed in a loop
  commit; left in place because it tests real infrastructure.
- ADR-0024 — worktree collaboration model.
- [[epic-fork-system]] (done at 3/8) — the multi-user editing
  infrastructure this WIP was building on.

## Discovery context

Stashed and ticketed during the 2026-06-09 PO-review grooming pass, after
the user confirmed the editor workflow had moved to Google Drive.
