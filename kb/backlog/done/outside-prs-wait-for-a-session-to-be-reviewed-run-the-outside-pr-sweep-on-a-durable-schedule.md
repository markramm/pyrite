---
id: outside-prs-wait-for-a-session-to-be-reviewed-run-the-outside-pr-sweep-on-a-durable-schedule
title: 'Outside PRs wait for someone to open a session before they are reviewed: run the outside-PR sweep on a durable schedule'
type: backlog_item
kind: process
tags:
- process
status: superseded
priority: high
effort: M
---

## Problem (retro 8, 2026-09-23)

The conductor skill says an outside PR "is reviewed in the tick it appears".
That holds only while a loop is running, and in the retro-8 window
(2026-09-20 01:50Z → 2026-09-23 16:45Z) no loop was running for most of the
time: session crons are session-bound and the last tick recorded in the desk
was 2026-09-20 08:45Z.

Measured over the 30 outside PRs merged in the window (7 contributors):

| Segment | p50 | p90 |
|---|---|---|
| created → first review comment | **3.3 h** | **9.6 h** |
| last push → merged (maintainer's wait) | 1.1 h | 5.7 h |
| created → merged, overall | 8.1 h | 33.3 h |

The maintainer merges quickly once a review exists; the slowest segment we
control is the *first* review, and it is slow because it waits for a human to
start a session. Today's instance: #318 opened 04:33Z, first reviewed ~16:40Z.
A first-time contributor's second round trip (the `--help` colour trap on #317
and #318) is paid on top of that wait each time.

## Proposal — needs the maintainer's decision (cost, and where it runs)

Run only the **outside-PR sweep** — not the whole tick — on a schedule that
survives the session: a `/schedule` cloud routine (or a launchd job running
`claude -p` on this machine) every 30–60 minutes that lists outside PRs with no
maintainer/conductor comment, runs the review.md pass and the cold read, and
posts the review comment. It never merges, never dispatches, never touches a
worktree it did not create. Everything else stays in the interactive loop.

Open questions the decision settles: cloud (needs the repo and a test runner in
the cloud environment; the suite is ~6 min at `-n 4`) vs this machine (bound by
the machine budget and the machine being awake); and the per-review cost.

## Acceptance

- Over the next 10 outside PRs after it is enabled: created → first review p50
  **≤ 1 h**, p90 **≤ 2 h**.
- No sweep review is contradicted by a later conductor review on the same head
  (the sweep's verdicts are as trustworthy as the tick's).
- Revert to session-only review if either fails over those 10.

## Superseded 2026-09-23

Declined by the maintainer: sub-10-hour first response is not an expectation for this project, and cloud routine runs are limited to a few a day. Replaced by `outside-prs-screen-before-anything-runs-review-after-ci-one-daily-routine`.
