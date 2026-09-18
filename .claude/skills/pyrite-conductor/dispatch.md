# Dispatch: composing themes and launching workers

How the conductor turns two trackers into reviewable units and hands each to
one worker in its own worktree. The old shared-tree wave protocol lives on
here in one form: **file footprints still decide what can run in parallel.**
With a worktree per worker an overlap no longer clobbers files; it surfaces
later, as a rebase conflict at the PR and as the semantic conflict nobody's
tests catch. Same planning, later and more expensive failure, so plan.

## 1. Compose themes

A theme is what a reviewer would recognize as one change. Test each candidate:

- Would the PR title make sense to someone who did not watch it being built?
- Is it complete — could it ship alone — rather than step one of three?
- Does it stay inside one area of the code, or does it cross layers for one
  reason (a fix that touches storage, service and endpoint is one theme; two
  unrelated fixes that happen to touch the same file are not)?

Group GitHub issues and backlog items by that test. Three small CLI bugs in
the entry write path are one theme; a docs correction is not a theme of its
own unless there is nothing else to batch it with — then it is, and the KB
fast path makes it a 30-second PR.

Write each theme down before dispatching, as the worker's spec:

```
Theme:       write-path correctness
Closes:      #15, #14, #16, #17
Acceptance:  (copied from each ticket, verbatim)
Touches:     pyrite/models/base.py (existing), pyrite/services/kb_service.py (existing),
             pyrite/schema/validators.py (existing), tests/ (new files)
Out of scope: the packaged web UI; anything in web/
Model:       opus   (cross-cutting; touches the base class and the service layer)
```

## 2. Footprints and sequencing

List the files each theme will modify (new files never conflict). Two
themes that modify the same file run **in sequence**: dispatch the first;
dispatch the second when the first's PR has merged, from a fresh
`scripts/new-worktree.sh` (so it branches from the merged `dev`). Do not try
to save time by running both and rebasing later — the rebase is where the
semantic conflict hides.

Cap: three workers when footprints overlap or a branch awaits review; **up to
six** when the themes are footprint-disjoint and fewer than two branches
await review (SKILL.md, "The cap is the review queue"). Each merge puts the
other open PRs `BEHIND`; a disjoint rebase is conflict-free but still re-runs
a ~3-minute gate, so past five or six in flight the tick is spent rebasing.

## 3. Create the worktree, then dispatch

Once per machine: the conductor's state lives in draft PR bodies and issue
threads, and the permission classifier refuses read-only `gh pr view --json
body` and merged-branch cleanup from inside an agent unless allowed (#72).
`.claude/settings.json` is gitignored here, so add this block to
`.claude/settings.local.json` on a fresh clone (maintainer-approved
2026-09-18):

```json
"Bash(gh pr view:*)", "Bash(gh pr list:*)", "Bash(gh pr checks:*)",
"Bash(gh issue view:*)", "Bash(gh issue list:*)",
"Bash(gh run view:*)", "Bash(gh run list:*)",
"Bash(git worktree list:*)", "Bash(git worktree remove:*)", "Bash(git worktree prune:*)",
"Bash(git branch -d:*)", "Bash(git branch -D:*)"
```

Write PR and issue bodies to a file and pass `--body-file`: a body passed
inline through `"$(cat <<'EOF' … )"` breaks on backticks and apostrophes in
the shell's eval (twice on 2026-09-18), and the failure looks like a
half-run command.

```bash
cd /Users/markr/pyrite && scripts/new-worktree.sh fix/<theme-slug>
#  -> /Users/markr/pyrite-wt/fix-<theme-slug>  with its own .venv and hooks
```

Then launch the worker with the Agent tool. Never use the tool's
`isolation: "worktree"` option (its base commit has been wrong before, and its
merge ceremony is what the script replaces); the worker is *told* its
worktree.

Agent types under `.claude/agents/` register when a session starts, so a
session that created or merged `pyrite-worker.md` will not have it (observed
2026-09-18). If `subagent_type="pyrite-worker"` is refused, dispatch
`subagent_type="general-purpose"` with the same `model` and paste the body of
`.claude/agents/pyrite-worker.md` at the top of the prompt; the next session
has the type.

```
Agent(
  subagent_type="pyrite-worker",
  model="sonnet" | "opus",
  description="theme: write-path correctness",
  prompt=<the spec above, plus:>
    "Work in /Users/markr/pyrite-wt/fix-<slug> on branch fix/<slug>. Use its
     .venv. Load the pyrite-dev skill and follow it. Do not open a PR. When
     the theme is complete, reply with the report format from pyrite-dev."
)
```

### Model by shape of work

| Shape | Model | Why |
|---|---|---|
| Well-specified, mechanical, clear acceptance (a slug fix, an exit code, a path default, a docs correction) | **sonnet** | the spec carries the judgment; speed and cost win |
| Design-shaped or cross-cutting (touches the base class, the service layer, auth, storage, a public interface; needs a root-cause investigation) | **opus** | the judgment is the work |
| A spike — the architect could not write acceptance criteria because a question is open (root cause unknown, two designs plausible, a dependency unverified) | **opus** (`pyrite-spike`) | the deliverable is a decision-ready ticket, not code; one tick, no PR |
| The conductor itself, and cold reads | the strongest available | reviewing is judgment |

When unsure, the tell is the ticket: if its acceptance criteria could be
handed to a careful junior engineer with no further conversation, sonnet.

### Prompt hygiene

A worker's prompt says which files are **new** and which are **existing and
to be patched minimally**. "Add feature X with endpoints, model and UI" leads
to rewrites of files it should have touched in two lines. Name the files.

Sub-agents a worker spawns share the worker's branch and worktree; the worker
gives them disjoint files, the same rule one level down.

## 4. While workers run

Do not poll. Workers report when done; the harness notifies you. Use the time
for the health check, absorbing earlier branches, or composing the next
themes. Never claim to know a worker's result before its report arrives.

## 5. When a worker reports

Go to [review.md](review.md). The report is where review *starts*, not where
it ends.
