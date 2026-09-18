# Review: from a worker's branch to a merged PR

The conductor's review is the reason the maintainer can review a PR in five
minutes. Everything here happens **before** `gh pr create`.

## The checklist

In the worker's worktree (`cd /Users/markr/pyrite-wt/<branch-dir>`):

```
- [ ] git log dev..HEAD --oneline        commits are focused, messages say why, Fixes #N present
- [ ] git diff dev...HEAD                 READ IT. Every hunk. The report is not the diff.
- [ ] .venv/bin/pytest tests/ extensions/ -n auto     green, here, now
- [ ] fix stashed, the new tests fail: `scripts/verify-red.sh <test-node-id> <impl file>...` — EVERY test
      named for a regression or a "still works" case, not one at random (PR #69: a class named for the
      exact regression it reintroduced covered only cases that already passed, and read as tested)
- [ ] any number in the report (faster, slower, N% fewer rewrites) was measured under ONE interpreter with
      the source tree pinned — each worktree has its own .venv and they resolve different Pythons; "run it
      here, then there" compares environments (PR #69: a published "not slower" and a cold read's "+71%"
      were both 3.11-vs-3.13 artefacts) — or the number is struck from the PR
- [ ] ruff check . && ruff format --check .
- [ ] theme complete? nothing in "Left:" that belongs to this PR
- [ ] CHANGELOG [Unreleased] has a line per user-visible change; KB updated via CLI where the theme touched it
- [ ] no private material, no absolute home paths (git grep -n "/Users/" -- the branch's new files)
- [ ] cold read needed? (below)
```

What you look for in the diff, beyond "does it work": a change the ticket
did not ask for; a test that asserts the implementation rather than the
behaviour; error handling that swallows; a public shape (CLI flag, REST
field, MCP tool argument) that changed without a note; anything the worker
marked "Unsure".

## Outcomes

- **Fix it yourself** when it is small and you are sure: commit on the
  branch with a message that says what and why.
- **Redispatch** when the theme is incomplete or the approach is wrong: same
  worktree, a prompt that quotes the specific gap. A fragment never becomes a
  PR.
- **Cold read** when the change is risky (below), then triage its findings
  the same way.

## The cold read

Dispatch `pyrite-reviewer` when the diff touches **`pyrite/server/`,
`pyrite/storage/`, `pyrite/schema/`, the auth code, or a public shape**, when
it deletes or weakens a test, when the worker's "Unsure" is non-empty, or
whenever your own reading felt too familiar to be critical. Docs and
mechanical fixes do not earn it.

The reviewer gets the diff and nothing else — no ticket, no report, no
conversation. Its value is that it has not been told what to expect.

```
Agent(
  subagent_type="pyrite-reviewer",
  description="cold read: <theme>",
  prompt="Review this change cold. Repository: /Users/markr/pyrite-wt/<dir>,
          branch <branch>, base dev. Run `git diff dev...HEAD`. You have no
          other context on purpose. Report per review.md's finding format."
)
```

Findings come back as: **what breaks** (a concrete input → wrong result),
**what erodes trust** (unclear, untested, surprising), **what is left on the
table** (the ticket's intent the change missed). Each with a file and line.
You decide: fix, redispatch, or note in the PR as a known trade-off. A
finding is evidence to check, not an order to obey — verify it the same way
you verify the worker.

## Open the PR

```bash
git push -u origin <branch>
gh pr create --base dev --title "<type>: <what, in one line a reviewer understands>" --body-file <body>
gh pr merge --auto --rebase
```

Body template:

```
<One paragraph: what a user or operator can now rely on that they could not before.>

<Numbered list, one item per commit or per closed ticket: what and why, one or two lines each. "Fixes #N" on each that closes an issue.>

<Evidence: the full-suite line; anything run beyond the suite (a live server check, an install from tag).>

<Known trade-offs or "Unsure" items the reviewer should look at, if any.>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

Rebase is the default merge; squash for a branch whose history is noise.

## Shepherd it

- Checks run ~30 s for docs/KB-only, ~3 min for code (one interpreter; the
  full matrix runs on `dev` after the merge).
- `gh pr view N --json mergeStateStatus` → `BEHIND` means another PR merged
  first: `gh pr update-branch N --rebase`. Auto-merge stays armed.
- Merged → `git worktree remove <dir> && git branch -d <branch>` from the main
  checkout, then `git pull --ff-only origin dev` there.
- Red after the merge on the `dev` push (the full matrix found something the
  PR's single interpreter did not) → that is the next theme, before any
  other dispatch.
