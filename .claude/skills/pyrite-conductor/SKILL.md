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
to want an ADR first. **Dispatch it on any tick where the ready queue —
themes that already have acceptance criteria, a footprint and a model — holds
fewer than twice the worker cap.** It is read-only and runs beside the
builds, so it costs the tick nothing but tokens, and a tick that dispatches
from titles is how two workers end up assigned rows of one table (retro 1).
**Keep a handful of `good first issue` items open at all times — at least
five.** The label is a dispatch signal to the outside world: on 2026-09-18
issues written with a verbatim error, a reproduction and acceptance
criteria drew four first-time contributors' PRs within an hour of being
labelled (#57 → #126 in 37 minutes; #97 → #108 and #116, twenty minutes
apart). The groom lane tops the pool up on every tick where the count has
fallen below five, from pool items that (a) a stranger could execute from
the issue alone — the error verbatim, steps, acceptance, the files; (b)
touch nothing security-adjacent (auth, permissions, the read-scoping
paths); (c) do not overlap a theme in flight or another open outside PR;
(d) are small. The architect writes the issue text to that standard before
the label goes on; a labelled issue that a review later finds unexecutable
is a groom-lane defect. Outside PRs are then reviewed by the sweep and
merged by the maintainer (see "Outside contributions jump the queue").

When the architect cannot write acceptance criteria because a question is
open — a root cause unknown, two designs plausible, a dependency's behaviour
unverified — it names a **spike** instead: dispatch `pyrite-spike` (one
tick, its own throwaway worktree, no PR) and its only deliverable is the
ticket changed: acceptance criteria that did not exist, an ADR draft marked
`proposed`, or "not feasible, because". A spike that returns prose and no
changed ticket is redispatched with the question sharpened, once. The conductor supplies the ordering itself from the
roadmap's definition of done (what unblocks what, what the release owes) and
turns the result into specs ([dispatch.md](dispatch.md)). Add a separate PM
read only when a tick demonstrably chose the wrong thing; until then it is
cost without evidence. Never dispatch a theme the architect flagged as
needing a decision the maintainer has kept.

**Build lane.** Workers in their own worktrees. **The draft PR is the
claim**, and the claim's first commit is the backlog item for the theme:
`gh pr create` refuses an empty branch (#73), so at dispatch the conductor
claims the item (`pyrite update <id> -k pyrite -f status=in_progress -f
assignee=agent:<worker>`; create one first with `pyrite create -k pyrite -t
backlog_item` when the theme is a group of GitHub issues with no item — the
theme *is* an item, and `pyrite sw backlog` should show it in flight),
commits that on the branch, pushes, and opens `gh pr create --draft --base
dev --body-file <spec>` with the theme spec as the body. The worker's report
is appended to that body; review flips it to ready (`gh pr ready`). One
place, visible to anyone with `gh pr list`, readable by the next tick with
no agent's memory, and the board agrees with it. Do not commit the spec as
a loose file (`.claude/THEME.md`): one reached `dev` in 22619c9 and
add/add-conflicted with every branch carrying its own (#106); the path is
now gitignored.

**Review lane.** [review.md](review.md), including the cold read.

**Outside contributions jump the queue.** A pull request from anyone but the
maintainer or Dependabot is reviewed in the tick it appears — before the
loop's own branches — and brought to the maintainer with the review
already done (maintainer, 2026-09-18: "they should be brought to my
attention with a review right away"). The health step lists them first:
`gh pr list --state open --json number,author,title --jq '.[] | select(.author.login != "markramm" and (.author.login | test("dependabot") | not))'`.
For each: claim it (`in-review`), `gh pr checkout` into a fresh worktree,
the full review.md pass with the cold read always on, then a review
comment on the PR in the template plus a plain-language recommendation —
merge; request these specific changes; wait for <PR> it conflicts with;
or, when two PRs fix one issue, which one and why, and what to credit from
the other. **Never merge it**: merging outside work is the maintainer's;
the report's "Needs the maintainer" section leads with it, with the
recommendation in one sentence. Note whether its CI run is
`action_required` (first-time contributors need the maintainer to approve
the workflow run) so the maintainer knows the gate has not spoken yet.

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

**One conductor at a time.** A tick is the *scheduled* one. A worker's
hand-back revives the tick agent that dispatched it; a revived tick does
exactly one thing — appends the worker's report to the draft PR body
(`gh pr edit N --body-file`) — and exits. It does not review, rebase, cold-read,
flip or redispatch. On 2026-09-18 four conductor agents were alive at once
(two revived, two scheduled): three reviewed one PR (#111), two published
contradictory verdicts ten seconds apart, one ran 1 h 46 m absorbing its own
dispatch (#114), and one did checkouts inside a worktree whose worker was
mid-pass, leaving 18 foreign commits one push from the wrong PR (#119). The
process had claims on themes and none on ticks or worktrees; this rule and
the two below give it both.

**The absorb lane takes only branches that had reported before the tick
began.** A worker that reports mid-tick is the next tick's absorb (#114). A
tick therefore has a bounded length — health, absorb what was waiting, groom,
dispatch, report — and stops; thirty minutes is long.

**A conductor never enters a worker's worktree.** Review from the pushed
head in your own worktree: `scripts/new-worktree.sh review/<slug>
origin/<branch>` (a detached checkout of the branch is fine), so the commit
you read is the commit the PR carries (#91: a green check is a claim about
a commit) and the worker's tree is never moved under it (#119). The worker's
report names the pushed SHA; if `origin/<branch>` is behind the report, the
branch is not reported yet.

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

- `dev` red: nothing merges until it is fixed. That is the first theme —
  and under a tripped breaker it is the one theme the host may dispatch
  without the maintainer, because leaving `dev` red is the worse default.
- A PR `BEHIND`: `gh pr update-branch N --rebase` (auto-merge does not do it).
- A merged branch with a worktree still present: `git worktree remove`, `git branch -d`.
- More than ~4 PRs open: stop dispatching; the gate is serialized.

### 2. Absorb: review before it becomes a PR

For each worker that reported done — protocol in [review.md](review.md):

1. Claim it (`in-review`). Check out the **pushed** head in your own review
   worktree — never the worker's. `git log origin/dev..HEAD --oneline`; read
   the **diff**, not the report.
2. Re-run `.venv/bin/pytest tests/ extensions/ -n auto` there yourself.
3. `scripts/verify-red.sh` on every regression-named test (exit 2 = no claim).
4. Is the theme complete? Would a reviewer see one coherent change?
5. Does it need a **cold read**? Yes if the diff touches `pyrite/server/`,
   `pyrite/storage/`, `pyrite/schema/`, the auth code, or a public shape
   (CLI flag, REST field, MCP tool argument, file format); deletes or
   weakens a test; or the worker's "Unsure" names a **design decision** —
   that last trigger is mandatory, not discretionary, and the reviewer's
   brief quotes the Unsure verbatim as its first question (#115: the
   conductor read a class named for the exact regression it reintroduced
   and was reassured by the name; the cold read was not). Dispatch
   `pyrite-reviewer` with the diff and no other context; triage its
   findings: fix, redispatch, or note in the PR as a known trade-off. The
   reviewer's report is model output too: reproduce a finding before acting
   on it, and never publish a number you did not measure under one
   interpreter against the merge base.
6. Then, and only then: push, `gh pr create --base dev`, body from the
   template in review.md, `gh pr merge --auto --rebase`. Watch it; rebase on
   `BEHIND`; clean up the worktree when it merges.

### 3. Choose: compose themes

If the ready queue is shorter than twice the worker cap, dispatch the
architect first (groom lane above) and compose from its breakdown; compose
by hand only what it already groomed. Read both surfaces, in this order:

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
the quality theme because features are waiting is how a codebase
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
auth/storage/server. **The cap is the review queue, not a number.** Three
workers when footprints overlap or a review is waiting; up to six when the
themes are footprint-disjoint (new files, separate spec files, separate
modules — the Playwright fan-out, an extension each) and fewer than two
branches await review. The constraint is this conductor's attention:
every worker returns a diff that needs 10–15 minutes of reading and a
suite run, so dispatch what the next tick can absorb, and stop dispatching
when the review queue is longer than that. The cap counts *workers*: the
week's tick-log PR and other record-only KB PRs are not in flight and do not
take a slot (retro 1, 2026-09-18: the log PR was counted, and the loop ran
at two workers while believing it was at three). Spikes count as workers.

Never `isolation: "worktree"` on the Agent tool — the script makes the
worktree, and the agent is told where it is.

### 5. Report, and leave the record

What merged (PR numbers, what they closed), what is in review and why it is
waiting, what was dispatched (theme, worker, model), what is blocked and on
whom. If the bottleneck has moved to the maintainer's desk (a decision, a
setting only they can change), say so and stop rather than ticking idle.

**Read the tick log by timestamp, not by position.** Entries are appended
by whichever conductor finishes first, so the newest tick can sit above an
older retro; before absorbing anything, `grep -n "^## " kb/notes/conductor-log-*.md`
and read the latest *timestamp*.

**Append the same report to the tick log** — `kb/notes/conductor-log-<YYYY-Www>.md`
(one note per ISO week; create it with `pyrite create -k pyrite -t note
--title "Conductor log <YYYY-Www>"` on the week's first tick, then append a
`## Tick <timestamp>` section and `pyrite index sync`). The retro reads this
log, not your memory; a tick that leaves no entry did not happen. The `dev`
ruleset takes nothing without a PR (#71), so the log lives on a weekly
branch: `scripts/new-worktree.sh kb/conductor-log-<YYYY-Www>` on the first
tick, one draft PR held open for the week, each tick commits and pushes
there; the retro flips it to ready. Never a PR per tick — each merge puts
every other open PR `BEHIND`.

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
delegated; landing repeatedly broken things is not. A breaker trip is a
retro trigger; the retro says what the theme needed that it did not get
(on 2026-09-18: a spike — the root cause of #46/#86/#87 was unknown when a
worker was dispatched to fix it, and the fix took three passes).

## References

- `poppendiecks` KB, `amplify-learning`: the value stream is knowledge, not
  code — the reason the record each tick leaves (the log, the ticket, the
  filed issue) is the product and not overhead.

- [dispatch.md](dispatch.md) — theme composition, footprints, prompt templates, model choice
- [review.md](review.md) — the review checklist, the cold-read dispatch, the PR template
- [release-runbook.md](release-runbook.md) — dev → main, tags, deploy
- The worker: [pyrite-dev](../pyrite-dev/SKILL.md) and its references (gotchas, tdd, testing)
