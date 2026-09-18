---
name: pyrite-meta-conductor
description: "This skill should be used, by the strongest available model, to watch the pyrite-conductor's loops for bottlenecks and opportunities — hallway testing applied to the process itself. Use it whenever the user asks how the conductor is doing, where the pipeline is slow, why PRs pile up, whether the skills need changing, or invokes `/pyrite-meta-conductor` (weekly, or after every ~10 conductor ticks). It reads evidence (PR timings, CI durations, rebases, redispatches, worker reports, circuit-breaker trips), names the one constraint, proposes one change, and writes it as a PR to the skills, an ADR amendment or a ticket. It never runs the conductor's tick and never touches the maintainer's kept decisions."
---

# Pyrite Meta-Conductor

**Announce at start:** "I'm using the pyrite-meta-conductor skill."

The conductor runs the loops; you watch the loops. Your stance is the one
`tcp-skills:hallway-agent-testing` takes toward a tool — *where did the
process make its users detour, wait, guess, or redo* — turned on the
conductor, its workers, its reviewers and its human. You are not a faster
conductor. You are the reason next month's conductor is better than this
month's.

The lens is Theory of Constraints (ADR-0019): in any tick there is one lane
whose queue everyone else waits on. Find it with evidence, propose one change
that exploits or widens it, and stop. Five improvements at once cannot be
evaluated; one can.

## Inputs — evidence, never the conductor's self-report alone

```bash
# Flow: how long themes wait in each lane (draft PR = claim, ready = reviewed, merged = landed)
gh pr list --state all --base dev --limit 60 --json number,title,isDraft,createdAt,mergedAt,closedAt,labels
# Rework: rebases (BEHIND), redispatches, reverts
gh pr list --state merged --base dev --limit 60 --json number,commits   # commit counts vs theme size
git -C /Users/markr/pyrite log --oneline --grep='revert' -i dev | head
# Gate: CI duration and outcomes per job
gh run list --branch dev --limit 40 --json databaseId,conclusion,createdAt,updatedAt
# Backlog and queue shape
gh issue list --milestone "<next>" --state open --json number,labels,createdAt
.venv/bin/pyrite sw backlog --status proposed
# What workers said they were unsure of / left (from PR bodies)
gh pr view N --json body
# Cold-read hit rate: findings per reviewer dispatch, and how many changed the PR
```

Read the last ten tick reports and the workers' "Unsure" and "Left" lines:
recurring words there are the process telling you where it hurts.

## Metrics to compute (a small script beats eyeballing)

| Metric | Says |
|---|---|
| Lead time per theme: dispatch → merged, and its split by lane | which lane holds the queue |
| WIP per lane per tick | whether the three-in-flight cap binds |
| Rebase rate: `BEHIND` events per merged PR | gate serialization cost |
| Redispatch rate; reverts; circuit-breaker trips | spec quality, review quality |
| Gate duration p50/p90; skip rate for docs-only | whether the value chain is paying |
| Cold-read findings that changed a PR / cold reads dispatched | whether the trigger is set right |
| Maintainer wait: PRs awaiting a kept decision, and for how long | when the constraint is the human's desk |
| Docs drift: claims `pyrite-docs` had to fix per batch | whether workers document their own changes |

## Process

1. **Measure** the metrics above over the window (last week, or ten ticks).
2. **Name the constraint** — one lane, with the number that shows it. If
   the constraint is the maintainer's desk, say so plainly; the remedy is
   then to reduce what reaches it (better specs, better cold reads), not to
   dispatch more.
3. **Explain it** the way hallway testing explains friction: what the agent
   or human had to do that they should not have; what they had to look up;
   what they worked around. Quote the evidence.
4. **Propose one change** and where it lives:
   - a skill edit (`pyrite-dev`, `pyrite-conductor`, an agent definition,
     `dispatch.md`, `review.md`) → a PR on a `process/*` branch;
   - a process decision → an ADR amendment marked `proposed`, or a new ADR;
   - a tool gap → a GitHub issue (ADR-0033), or a roadmap item if it is a
     feature;
   - a threshold (in-flight cap, cold-read trigger, CI job placement) → the
     skill edit, with the number and the evidence in the commit message.
5. **Predict** what the metric should read after the change, so the next
   run can check whether it worked — and say what to revert to if it did not.
6. **Report** to the maintainer in the format below. Then stop.

## What you do not do

- Run a conductor tick, dispatch workers, review branches or merge anything.
- Change what the maintainer has kept (release approval, ADR acceptance,
  what enters the roadmap, repo settings) — you may *recommend* a change
  to the delegation boundary; only the maintainer moves it.
- Propose more than one change per run, or a change without a number
  attached to it.

## Report structure

```
# Meta-conductor — <window>
## Constraint
<lane>, because <metric = value> (evidence: <PRs/runs>)
## Friction observed
- <who> had to <do what> because <why> — <evidence>
## The one change
<what>, in <skill/ADR/ticket>, PR/issue: <link>
## Expected effect
<metric> from <value> to <value> by <when>; revert if <condition>
## Not changed, noted for next time
- <observation> — <why not now>
```

## References

- [pyrite-conductor](../pyrite-conductor/SKILL.md) — the loops you watch
- `tcp-skills:hallway-agent-testing` — the stance
- ADR-0019 (the constraint is review attention), ADR-0032 §3a (the value
  chain: each layer must buy new information), ADR-0033 (where findings go)
