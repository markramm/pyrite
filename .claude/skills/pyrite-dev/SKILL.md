---
name: pyrite-dev
description: "This skill should be used by an agent developing Pyrite code — fixing a bug, adding a feature, writing or running tests, debugging, or completing a backlog item — on its own branch in its own worktree. Enforces TDD, root-cause debugging and evidence-before-claims, and ends with a report the conductor can review. For picking work, dispatching agents, reviewing branches, opening PRs, releasing or deploying, use pyrite-conductor."
---

# Pyrite Development Skill (the worker)

**Announce at start:** "I'm using the pyrite-dev skill."

You develop Pyrite code on **one branch, in one worktree, on one theme**. You
do not pick the theme, you do not open the pull request, and you never touch
`dev`. Those belong to [pyrite-conductor](../pyrite-conductor/SKILL.md). If
you are the only agent in the session — nobody dispatched you — you are also
the conductor: finish the work here, then load pyrite-conductor for the review
and PR steps.

## The Iron Laws

```
1. NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
2. NO FIX ATTEMPTS WITHOUT ROOT CAUSE INVESTIGATION
3. NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
4. NO BACKLOG CHANGES WITHOUT USING THE CLI (`pyrite update`, `pyrite create`)
```

Thinking "skip this just once"? That's rationalization. These exist because
skipping them always costs more time than following them.

---

## Where you are

```bash
git branch --show-current     # a feature/*, fix/*, kb/* branch -- never dev
pwd                           # a worktree under ../pyrite-wt/, with its own .venv
.venv/bin/pyrite kb list      # the `pyrite` KB path must be THIS worktree's kb/
```

The last line matters: `pyrite -k pyrite` resolves through a config, and
without the worktree's own `.pyrite/config.yaml` it resolves through
`~/.pyrite` to the *main* checkout -- every ticket update you make lands in
the wrong tree. `scripts/new-worktree.sh` writes the local config; if `kb
list` shows `/Users/markr/pyrite/kb`, stop and create it before any KB
command.

If either is wrong, stop: `scripts/new-worktree.sh <branch>` from the main
checkout creates the right place (ADR-0032). Use `.venv/bin/...` from the
worktree; the main checkout's venv imports the main checkout's code.

Sub-agents you spawn share **your** branch and worktree. Do not give them
`isolation: "worktree"`; give them disjoint files (see the conductor's
[dispatch.md](../pyrite-conductor/dispatch.md) for footprint rules).

## Before writing code

```
- [ ] Read the ticket: the GitHub issue (`gh issue view N`) or the backlog item
      (`pyrite get <id> -k pyrite`), and its acceptance criteria
- [ ] `pyrite search "<topic>" -k pyrite` -- ADRs and designs that constrain the change
- [ ] Check kb/adrs/ for relevant architecture decisions
- [ ] Identify which files need to change (see [architecture.md](architecture.md))
- [ ] Check existing tests for the area; `gh issue list --label <area>` for known bugs
- [ ] If multi-step: create tasks with TaskCreate, set dependencies
```

Two trackers, one rule (ADR-0033): **bugs and user requests live in GitHub
Issues; the roadmap (epics, backlog items, ADRs) lives in `kb/`.** A bug you
fix in the same PR that found it needs no issue; the commit says `Fixes #N`.
A bug you find and do not fix: `gh issue create --label bug --label <area>`,
with placeholders for anything private. New roadmap work: a backlog item via
the CLI. Never both.

## Test-Driven Development

**RED → GREEN → REFACTOR. No exceptions.** Detailed patterns: [tdd.md](tdd.md).

1. **RED** — one failing test showing the desired behaviour
2. **Verify RED** — run it; confirm it fails for the right reason
3. **GREEN** — the minimal code that passes. Nothing more.
4. **Verify GREEN** — run it, and the tests around it
5. **REFACTOR** — clean up while staying green
6. **Commit** — small, focused, conventional-commit prefix; `Fixes #N` for a bug

Wrote code before the test? Delete it and start over.

| Rationalization | Reality |
|---|---|
| "Too simple to test" | Simple code breaks. The test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Manual test faster" | Manual doesn't prove edge cases. Can't re-run. |

## Systematic Debugging

**Investigate root cause before attempting fixes.** Full process:
[debugging.md](debugging.md).

1. Read the error carefully — stack trace, line numbers, exact message
2. Reproduce consistently
3. Check recent changes (`git log`, `git diff`)
4. Trace the data flow backward to where the bad value originates
5. Form a hypothesis, test one variable at a time
6. Fix at the root cause, not the symptom

**If 3+ fix attempts fail:** stop, question the architecture, say so in your
report.

## Verification Before Completion

**Evidence before claims. Always.** Identify the command that proves the
claim, run it in full, read the output, then claim.

| Claim | Run | Look for |
|---|---|---|
| Backend tests pass | `.venv/bin/pytest tests/ extensions/ -n auto` | `N passed, 0 failed` |
| The fix is real | the new test, with the fix reverted (`git stash`) | it fails |
| Frontend passes | `cd web && npm run check && npm run test:unit && npm run build` | all green |
| Lint passes | `.venv/bin/ruff check . && .venv/bin/ruff format --check .` | clean |
| KB content findable | `.venv/bin/pyrite search "<feature>" -k pyrite` | it appears |

Forbidden without evidence: "should work", "looks correct", "probably
passes", "I'm confident".

The suite runs in parallel. A test that passes alone and fails under
`-n auto` is a bug in that test (shared state, a fixed timeout, an unclosed
database), not a reason to run serially.

## KB bookkeeping for your theme

Use the CLI, never hand-edit frontmatter. Do this on your branch; the
conductor reviews it with the code.

- Closed a backlog item?
  `pyrite update <id> -k pyrite -f status=done && git mv kb/backlog/<id>.md kb/backlog/done/`
  (`done`, never `completed` — off-enum; see [gotchas.md](gotchas.md))
- Changed architecture or added a component? `pyrite create -k pyrite -t component ...`
  or `pyrite sw new-adr "Title" -k pyrite --status proposed`
- Hit a surprising behaviour? Append to [gotchas.md](gotchas.md).
- Then `.venv/bin/pyrite index sync` and check `pyrite search` finds it.
- One user-visible change, one **changelog fragment**: a new file
  `changelog.d/<slug>.<section>.md` (sections: `added changed deprecated
  removed fixed security`) holding the bullet as it should read in the release
  notes. **Never edit `CHANGELOG.md`** — `[Unreleased]` is empty on `dev` and a
  test asserts it. Every branch appending to one file is why five PRs
  conflicted in a session (#243); a fragment's path is yours alone, so a rebase
  has nothing to resolve. See `changelog.d/README.md`.

## Finishing: the report

You are done when the theme is complete — not a fragment of it — and every
claim below has evidence. Your last three acts, in order: **diff your
footprint against the theme's out-of-scope list** (`git diff --name-only
origin/dev...HEAD`; anything on that list means something entered your
branch that is not yours — on 2026-09-18 a worker found 18 foreign commits
this way, one push from the wrong PR, #119); **push** (`git push -u origin
<branch>`; a red pre-push is a stop, never `--no-verify`); **report with the
pushed SHA** — a conductor reviews only what is on the remote. Do **not**
open a PR. Report:

```
Branch:   fix/what-it-fixes      Worktree: ../pyrite-wt/fix-what-it-fixes
Pushed:   <sha> == origin/<branch>
Commits:  <n>, listed with one line each
Closes:   #N, #M  (or the backlog item ids)
Evidence: full suite output line; the RED run of each new test; lint
Changed:  files touched, new vs existing
Unsure:   anything a reviewer should look at twice, or a decision that could
          have gone another way
Left:     anything in the theme you did not finish, and why
```

A conductor will read the diff and re-run the suite before opening the PR;
make that cheap by keeping commits focused and the report honest.

---

## References

- [architecture.md](architecture.md) — where things live
- [tdd.md](tdd.md), [testing.md](testing.md), [debugging.md](debugging.md)
- [data-pipelines.md](data-pipelines.md) — the entry lifecycle
- [extensions.md](extensions.md) — building a plugin
- [gotchas.md](gotchas.md) — known pitfalls; read before touching hooks, DB access, entry ids
- `kb/adrs/` — run `pyrite sw adrs`; ADR-0032 (branch flow) and ADR-0033 (where work is tracked) govern process
