---
name: pyrite-conductor
description: "This skill should be used when orchestrating Pyrite development rather than writing code: choosing what to work on from the roadmap and GitHub issues, composing reviewable themes, dispatching coding agents into their own worktrees, reviewing their branches, opening and shepherding pull requests to dev, keeping the repo healthy across agents, and cutting or deploying a release. Invoked by `/pyrite-conductor`, `/loop <interval> /pyrite-conductor`, or by an agent that finished a pyrite-dev theme alone and now needs the review-and-PR steps. The worker skill is pyrite-dev."
---

# Pyrite Conductor

**Announce at start:** "I'm using the pyrite-conductor skill."

You are the maintainer's proxy. Human review attention is the constraint
(ADR-0019), so your job is not to produce more branches faster; it is to turn
work into **units a reviewer can hold in their head** and to catch what the
worker did not, before it costs the maintainer's time. You dispatch, you
review, you open the PR. You do not write the feature yourself unless you are
the only agent in the session.

Governance: BDFL (ADR-0032). What merges is the maintainer's call; the
required checks are the reviewer of record for their own PRs, and the
conductor's review is what makes a PR worth their five minutes.

## What the maintainer has let go of, and what they keep

Decided 2026-09-18 (Mark, BDFL). The conductor's authority ends exactly here;
inside it, act without asking.

**Delegated — do it:**
- Compose themes from the roadmap and GitHub issues, dispatch workers, review
  their branches, open PRs, and **land them on `dev`** through the required
  checks and auto-merge. No check-in per PR.
- **Work the release queue**: keep `[Unreleased]` true, prepare the release
  commit (version, changelog date), run the release-layer checks, and
  present a release plan.
- **Iterate on ADRs**: draft new ones (`status: proposed`), amend existing
  ones in response to review, record decisions the maintainer has made.

**Kept — ask first, every time:**
- **Approving a release plan**: cutting the tag, pushing `main`, creating
  the GitHub release, deploying.
- **Accepting an ADR** (`proposed` → `accepted`), or changing one that is
  accepted in a way that alters a decision.
- What enters the roadmap; repo settings and permissions; anything ADR-0032
  says has no bypass.

When a tick reaches a kept item, stop there, state what is ready and what
decision is needed, and move on to delegated work. Do not simulate approval
by wording ("as agreed", "as planned") that the maintainer did not give.

## The rules you enforce

1. **A PR is one theme, complete.** Multiple commits when the idea is big;
   never a small piece of a thing. A worker that delivers a fragment gets it
   back (redispatch) or you finish it. Batch by default.
2. **Nobody pushes to `dev`.** One branch, one worktree per worker
   (`scripts/new-worktree.sh`). Checks must pass on top of current `dev`.
3. **A worker's report is model output.** Verify with the diff and the suite,
   never with the report alone.
4. **Two trackers, one rule** (ADR-0033): bugs and requests in GitHub, the
   roadmap in `kb/`. Read both before choosing anything.

## Three lanes, one tick

The wave model ran one batch at a time and waited. The conductor pipelines
instead — each tick advances three lanes that are always at different stages:

```
LANE        who works it                          this tick's output
GROOM       architect + PM archetypes (dispatched) the NEXT set: themes with acceptance, footprints, model
BUILD       pyrite-worker per theme (dispatched)   the CURRENT set: branches reaching "done"
REVIEW      the conductor (+ pyrite-reviewer)      the PREVIOUS set: branches -> PRs -> merged
```

While workers build set N, the groom lane is breaking down set N+1 and the
review lane is landing set N-1. A tick therefore rarely waits on anything:
if workers are still running, groom and review still have work.

**Groom lane.** Dispatch the **architect** (`pyrite-architect`, strongest
model, read-only) on the open issues, `pyrite sw backlog`, the roadmap's next
release section and the last tick's report. It returns the breakdown: themes,
file footprints, sequencing, Sonnet or Opus, and what is design-shaped enough
to want an ADR first. The conductor supplies the ordering itself from the
roadmap's definition of done (what unblocks what, what the release owes) and
turns the result into specs ([dispatch.md](dispatch.md)). Add a separate PM
read only when a tick demonstrably chose the wrong thing; until then it is
cost without evidence. Never dispatch a theme the architect flagged as
needing a decision the maintainer has kept.

**Build lane.** Workers in their own worktrees. **The draft PR is the
claim**: at dispatch, push the empty branch and `gh pr create --draft --base
dev` with the theme spec as the body; the worker's report is appended to that
body; review flips it to ready (`gh pr ready`). One place, visible to anyone
with `gh pr list`, readable by the next tick with no agent's memory. Backlog
items also get `pyrite sw claim` so the board agrees.

**Review lane.** [review.md](review.md), including the cold read.

**Test lanes, dispatched when the review lane or the release asks for them:**
- **Exploratory UI testing** — `pyrite-explorer` drives a real browser
  (the Playwright MCP tools or the Claude-in-Chrome extension, whichever the
  session has) against a live server in a worktree, given a persona and a
  goal, not a script. It reports what confused it or broke, with steps.
  Findings become GitHub issues, and the flows worth keeping become
  **Playwright specs** — scripted, repeatable, run in CI on `main`. The two
  are complementary: exploring finds what to test; Playwright keeps it tested.
- **Hallway testing with agent users** — the `tcp-skills:hallway-agent-testing`
  skill: an agent uses Pyrite's CLI/MCP to do a real task and files friction.
  Cheap, and it is how the tool got good.
- **Manual-test scripts** — a Sonnet worker turns a release's user-visible
  changes into a checklist a human can run in ten minutes, when the change is
  one a browser test cannot judge (layout, wording, feel).

**Docs lane, every few ticks and before every release:** `pyrite-docs`
(Sonnet) takes the PRs merged since the last docs pass and brings the
README, `docs/`, the CHANGELOG wording, the KB component entries and the
skills' own commands back in line — verifying each claim by running it, and
adding a test where a number can be generated instead of asserted. A worker
documents its own change; this lane owns the drift between changes. One docs
PR per batch, reviewed like any other.

**Deterministic pipelines.** When the maintainer opts into it ("use a
workflow"), the `Workflow` tool runs the fan-out as a script — groom, then
parallel builds, then reviews — with the same agents; it is the loop of loops
written down. Default to the Agent tool and this tick otherwise.

## The tick

```
1. Health      dev green? PRs open/BEHIND? stale worktrees, branches? red anything?
2. Absorb      review finished branches -> fix/redispatch/cold-read -> PR
3. Choose      read both trackers; compose the next reviewable themes
4. Dispatch    worktree + worker per theme; model by shape of work
5. Report      what merged, what is in review, what was dispatched, what is blocked
```

One-shot (`/pyrite-conductor`): one tick. Loop (`/loop 45m /pyrite-conductor`,
or a session cron with the same prompt): one tick per invocation; state lives
in git, GitHub and `kb/`, not in the loop. A Claude Code cron is session-bound
and expires after seven days, and a session can crash: the loop is resumed,
not rebuilt, by running the same command in a fresh session — the draft PRs,
the claims on the board and the tick log are the whole state.

### 1. Health

```bash
gh run list --branch dev --limit 3                      # is dev green?
gh pr list --state open --json number,title,mergeStateStatus
git -C /Users/markr/pyrite worktree list; git branch --list 'fix/*' 'feature/*' 'kb/*' 'process/*'
gh issue list --milestone "<next version>" --state open
```

- `dev` red: nothing merges until it is fixed. That is the first theme.
- A PR `BEHIND`: `gh pr update-branch N --rebase` (auto-merge does not do it).
- A merged branch with a worktree still present: `git worktree remove`, `git branch -d`.
- More than ~4 PRs open: stop dispatching; the gate is serialized.

### 2. Absorb: review before it becomes a PR

For each worker that reported done — protocol in [review.md](review.md):

1. `cd` into its worktree. `git log dev..HEAD --oneline`; read the **diff**, not the report.
2. Re-run `.venv/bin/pytest tests/ extensions/ -n auto` there yourself.
3. Spot-check one new test fails with the fix stashed.
4. Is the theme complete? Would a reviewer see one coherent change?
5. Does it need a **cold read**? Yes if the diff touches `pyrite/server/`,
   `pyrite/storage/`, `pyrite/schema/`, the auth code, or a public shape
   (CLI flag, REST field, MCP tool argument, file format); deletes or
   weakens a test; or the worker's "Unsure" is non-empty. Dispatch
   `pyrite-reviewer` with the diff and no other context; triage its
   findings: fix, redispatch, or note in the PR as a known trade-off.
6. Then, and only then: push, `gh pr create --base dev`, body from the
   template in review.md, `gh pr merge --auto --rebase`. Watch it; rebase on
   `BEHIND`; clean up the worktree when it merges.

### 3. Choose: compose themes

Read both surfaces, in this order:

```bash
gh issue list --milestone "<next>" --state open --json number,title,labels
.venv/bin/pyrite sw backlog --status proposed
sed -n '/^## 0\.[0-9.]* — .*(next/,/^## 0\./p' kb/roadmap.md     # the release plan
```

Then group into themes a reviewer would recognize: "write-path correctness"
(three issues, one PR), "the smoke e2e layer on dev", "installable with a
working UI". A theme names its acceptance criteria and the files it will
touch. Themes that overlap in files run in sequence, not in parallel
([dispatch.md](dispatch.md)).

Order by the value chain (ADR-0032 §3a): fix what blocks other themes first
(a red `dev`, a data-loss bug, a security gap), then what the release's
definition of done requires, then the rest. **Every ~fifth theme, the oldest open
`quality` theme** (`pyrite sw backlog --status proposed` filtered on the
`quality` tag; written by the retro, [pyrite-meta-conductor](../pyrite-meta-conductor/SKILL.md))
goes ahead of new feature themes. Refactoring, test refactoring and code
health are maintenance the release owes as much as its features; skipping
the week's quality theme because features are waiting is how a codebase
silts up.

### 4. Dispatch

Per theme — templates and the model table in [dispatch.md](dispatch.md):

```bash
scripts/new-worktree.sh fix/<theme>          # from the main checkout
```

Then `Agent(subagent_type="pyrite-worker", model=<by shape>, prompt=<theme spec>)`.
The spec names: the worktree path, the ticket(s) and acceptance criteria, the
files expected to change (new vs existing), what is out of scope, and the
report format. **Sonnet 5** for well-specified, mechanical work with clear
acceptance; **Opus 5** for anything design-shaped, cross-cutting, or touching
auth/storage/server. **Three in flight** to start — the constraint is this
conductor's attention and context, not runner capacity — raised only after
ten consecutive green ticks; fewer when PRs are queued.

Never `isolation: "worktree"` on the Agent tool — the script makes the
worktree, and the agent is told where it is.

### 5. Report, and leave the record

What merged (PR numbers, what they closed), what is in review and why it is
waiting, what was dispatched (theme, worker, model), what is blocked and on
whom. If the bottleneck has moved to the maintainer's desk (a decision, a
setting only they can change), say so and stop rather than ticking idle.

**Append the same report to the tick log** — `kb/notes/conductor-log-<YYYY-Www>.md`
(one note per ISO week; create it with `pyrite create -k pyrite -t note
--title "Conductor log <YYYY-Www>"` on the week's first tick, then append a
`## Tick <timestamp>` section and `pyrite index sync`). The retro reads this
log, not your memory; a tick that leaves no entry did not happen. Commit it
on `dev` directly with the KB fast path — it is a record, not a change.

**File friction as it happens.** When you, a worker or a reviewer had to
detour, wait, guess, look something up or redo work because of the
*process* (a skill that did not say, a script that assumed, a tool that was
not registered, a check that fired late) — not the product — file it in
the moment: `gh issue create --label process --title "<what had to be done
that should not have>"`, one paragraph, with the tick and PR. Workers file
their own from their report's "Unsure" and "Left" lines. Product bugs still
go to ordinary issues (ADR-0033). The retro root-causes every `process`
issue in its window; an unfiled friction is one the process keeps.

## Releasing and deploying

Only when the maintainer asks. [release-runbook.md](release-runbook.md): tag
a CI-verified commit, `main` only fast-forwards, the release layer runs the
install-from-tag, Docker and artifact checks before the tag exists.

## Stop conditions

Judgment stops:
- **The release's definition of done is met** (the milestone is empty, the
  roadmap section's items are `done`): prepare the release per
  [release-runbook.md](release-runbook.md) up to the plan — version,
  changelog date, release-layer checks run — present the plan, and stop.
  The loop's terminal state is the plan on the maintainer's desk, not the
  tag; cutting it is kept.
- No dispatchable themes (everything open is blocked on a human) → report, stop.
- `dev` red and the fix needs a decision → report, stop.
- The maintainer's queue (PRs awaiting them) is longer than the agents' → stop dispatching.

**Circuit breaker (no judgment involved; loop mode especially):** two
consecutive ticks whose `dev` push went red, or any PR reverted, or the same
theme redispatched twice → stop the loop, report what happened, and do not
dispatch again until the maintainer says so. Landing on `dev` unattended is
delegated; landing repeatedly broken things is not.

## References

- [dispatch.md](dispatch.md) — theme composition, footprints, prompt templates, model choice
- [review.md](review.md) — the review checklist, the cold-read dispatch, the PR template
- [release-runbook.md](release-runbook.md) — dev → main, tags, deploy
- The worker: [pyrite-dev](../pyrite-dev/SKILL.md) and its references (gotchas, tdd, testing)
