---
id: worktree-merge-queue
type: backlog_item
title: "Admin merge queue: review and integrate user submissions"
kind: feature
status: proposed
priority: high
effort: M
tags: [web, git, collaboration, admin]
links:
- target: epic-fork-system
  relation: subtask_of
  kb: pyrite
- target: worktree-write-routing
  relation: blocked_by
  kb: pyrite
- target: adr-0024
  relation: tracks
  kb: pyrite
---

## Problem

After users edit entries in their worktrees, they need a way to submit changes for integration into main, and the admin needs a way to review and merge them.

## Scope

### User side
- "Submit changes" button in the web UI (visible when user has uncommitted or unsubmitted changes)
- Sets `submitted_at` timestamp on the user's worktree record
- Shows submission status: "Pending review", "Merged", "Rejected (with feedback)"

### Admin side
- Merge queue page (`/settings/merge-queue` or `/admin/merge-queue`)
- Lists all submitted branches with: username, submission date, files changed count
- Per-submission: entry-level diff against main (side-by-side or unified)
- Accept button: `git merge user/{name}` into main, rebase user worktree, push to upstream if configured
- Reject button: with optional feedback message, clears submitted flag

### API endpoints
- `POST /api/worktree/submit` — mark user's branch as submitted
- `GET /api/admin/merge-queue` — list submitted worktrees
- `GET /api/admin/merge-queue/{username}/diff` — diff against main
- `POST /api/admin/merge-queue/{username}/merge` — merge into main
- `POST /api/admin/merge-queue/{username}/reject` — reject with feedback

## Acceptance Criteria

- Users can submit their worktree changes with one click
- Admin sees all pending submissions with diffs
- Admin can merge or reject with feedback
- After merge, user's worktree is rebased to updated main
- After merge, main branch index is updated
