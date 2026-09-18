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

**Groom lane.** Dispatch two read-only agents on the same inputs (the open
issues, `pyrite sw backlog`, the roadmap's next release, the last tick's
report) and reconcile their outputs yourself:
- the **architect** (`pyrite-architect`, strongest model) reads the code the
  candidates touch and produces the breakdown: themes, file footprints,
  sequencing, which need Opus and which Sonnet, what is design-shaped enough
  to want an ADR first;
- the **PM** reads the trackers and the roadmap's definition of done and
  produces the ordering: what unblocks what, what the release owes, what a
  user would notice.
The conductor merges the two into specs ([dispatch.md](dispatch.md)) and
does not dispatch a theme the architect flagged as needing a decision the
maintainer has kept.

**Build lane.** Workers in their own worktrees; the kanban carries state
(`pyrite sw claim` / `sw submit` / `sw review-queue`, or the GitHub issue's
assignee for issue-driven themes), so a tick can read who holds what without
a running agent's memory.

**Review lane.** [review.md](review.md), including the cold read.

**Test lanes, dispatched when the review lane or the release asks for them:**
- **Exploratory UI testing** — an agent with the Playwright MCP tools
  (`browser_navigate`, `browser_snapshot`, `browser_click`, ...) against a
  live server in a worktree, given a persona and a goal, not a script. It
  reports what confused it or broke, with steps; findings become issues or
  spec additions. This is where a new screen earns its Playwright spec.
- **Hallway testing with agent users** — the `tcp-skills:hallway-agent-testing`
  skill: an agent uses Pyrite's CLI/MCP to do a real task and files friction.
  Cheap, and it is how the tool got good.
- **Manual-test scripts** — a Sonnet worker turns a release's user-visible
  changes into a checklist a human can run in ten minutes, when the change is
  one a browser test cannot judge (layout, wording, feel).

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

One-shot (`/pyrite-conductor`): one tick. Loop (`/loop 20m /pyrite-conductor`):
one tick per invocation; state lives in git, GitHub and `kb/`, not in the loop.

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
5. Does it need a **cold read**? Yes if it touches auth, storage, the server, a public
   interface (CLI/REST/MCP shape), or more than ~10 files. Dispatch the
   `pyrite-reviewer` agent with the diff and no other context; triage its
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
definition of done requires, then the rest.

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
auth/storage/server. 4–6 workers at most; fewer when PRs are queued.

Never `isolation: "worktree"` on the Agent tool — the script makes the
worktree, and the agent is told where it is.

### 5. Report

What merged (PR numbers, what they closed), what is in review and why it is
waiting, what was dispatched (theme, worker, model), what is blocked and on
whom. If the bottleneck has moved to the maintainer's desk (a decision, a
setting only they can change), say so and stop rather than ticking idle.

## Releasing and deploying

Only when the maintainer asks. [release-runbook.md](release-runbook.md): tag
a CI-verified commit, `main` only fast-forwards, the release layer runs the
install-from-tag, Docker and artifact checks before the tag exists.

## Stop conditions

- No dispatchable themes (everything open is blocked on a human) → report, stop.
- `dev` red and the fix needs a decision → report, stop.
- The maintainer's queue (PRs awaiting them) is longer than the agents' → stop dispatching.

## References

- [dispatch.md](dispatch.md) — theme composition, footprints, prompt templates, model choice
- [review.md](review.md) — the review checklist, the cold-read dispatch, the PR template
- [release-runbook.md](release-runbook.md) — dev → main, tags, deploy
- The worker: [pyrite-dev](../pyrite-dev/SKILL.md) and its references (gotchas, tdd, testing)
