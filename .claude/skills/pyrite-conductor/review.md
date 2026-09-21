# Review: from a worker's branch to a merged PR

The conductor's review is the reason the maintainer can review a PR in five
minutes. Everything here happens **before** `gh pr create`.

## The checklist

**Claim the review first.** More than one conductor can be alive at once —
a tick revived by its worker's hand-back, the scheduled tick, the host — and
on 2026-09-18 two of them cold-read PR #69 in parallel and a third rebased
it (#111). Before reading a diff: `gh pr view N --json labels`; if
`in-review` is set, skip the PR this tick. Otherwise `gh pr edit N
--add-label in-review`, and remove the label when you flip it to ready,
redispatch it, or stop reviewing it. A label older than an hour with no
comment from its owner is stale: take it over and say so on the PR.

**A red pre-push during a rebase is a stop, not a bypass.** The conductor
rebases branches while workers are editing `tests/` in sibling worktrees,
which is exactly when the shared pre-push suite is flaky (#112: a teardown
race, then an xdist collection mismatch). Do not `--no-verify`; the
permission layer refuses it for a reason. Re-run once; if it is still red,
say which test and hand the branch back to its worker with the rebase
undone (`git rebase --abort` or `git reset --hard origin/<branch>`), or
wait for the sibling to finish. A conductor that pushes through a red
pre-push has turned the value chain's first gate off for itself.

In **your own review worktree** on the pushed head — never the worker's
(`scripts/new-worktree.sh review/<slug> origin/<branch>`; #119). First:
`git rev-parse HEAD` equals the SHA in the worker's report and
`gh pr view N --json headRefOid`; a green check is a claim about a commit,
so identify the commit before believing the check (#91 — a docs-only
classification of an unpushed branch once reported `gate: success` for
code nobody had pushed).

```
- [ ] git log dev..HEAD --oneline        commits are focused, messages say why, Fixes #N present
- [ ] git diff dev...HEAD                 READ IT. Every hunk. The report is not the diff.
- [ ] before trusting a suite number, `python -c 'import pyrite, <ext_pkg>; print(...)'` must point into
      the worktree; make review worktrees with `scripts/new-worktree.sh` (never a symlinked .venv — #189,
      a review worktree whose .venv symlinked the main checkout's resolved every extension package to an
      editable install on `dev`, not the branch under review, and a suite number measured that way is not
      evidence)
- [ ] .venv/bin/pytest tests/ extensions/ -n auto     green, here, now
- [ ] fix reverted to the merge base, the new tests fail: `scripts/verify-red.sh <test-node-id> <impl file>...`
      (exit 0 = red without the fix; exit 1 = passes anyway; exit 2 = nothing was reverted, NO claim — #121) — EVERY test
      named for a regression or a "still works" case, not one at random (PR #69: a class named for the
      exact regression it reintroduced covered only cases that already passed, and read as tested)
- [ ] any number in the report (faster, slower, N% fewer rewrites, a flake rate) was measured against the
      MERGE BASE, under ONE interpreter with the source tree pinned, and the sentence that reports it states
      the condition — two sessions each published a confident wrong number about #69 in one window (one
      across two venvs, one against dev instead of the merge base) — each worktree has its own .venv and they resolve different Pythons; "run it
      here, then there" compares environments (PR #69: a published "not slower" and a cold read's "+71%"
      were both 3.11-vs-3.13 artefacts) — or the number is struck from the PR
- [ ] ruff check . && ruff format --check .
- [ ] theme complete? nothing in "Left:" that belongs to this PR
- [ ] a changelog fragment `changelog.d/<slug>.<section>.md` per user-visible change, and CHANGELOG.md
      NOT edited (a bullet under [Unreleased] is the conflict #243 removed; tests/test_changelog_fragments.py
      fails on one); KB updated via CLI where the theme touched it
- [ ] no private material, no absolute home paths (git grep -n "/Users/" -- the branch's new files)
- [ ] the diff stays inside the theme's footprint: nothing from another theme's out-of-scope list (#119 — 18
      foreign commits were one push from the wrong PR; the worker caught it, the reviewer must too)
- [ ] cold read needed? (below)
```

What you look for in the diff, beyond "does it work": a change the ticket
did not ask for; a test that asserts the implementation rather than the
behaviour; error handling that swallows; a public shape (CLI flag, REST
field, MCP tool argument) that changed without a note; anything the worker
marked "Unsure".

## Outside contributors' PRs

Same checklist, three differences. The cold read is always on (the author
is unknown to the loop and the reviewer's job is to be unimpressed). The
review comment is written for a person who is not on the team: say what
was checked and what was found, thank them for what is good specifically,
and ask for changes as a list they can act on without a second round of
questions. And the outcome is never "merge": it is a recommendation to the
maintainer — merge as is; merge after these changes; wait for <PR>; or,
for competing PRs on one issue, which one, why, and what the other one got
right that should be credited or folded in. Two PRs for #97 arrived twenty
minutes apart on 2026-09-18; that will happen again now that issues carry
reproductions.

**Bodies go through files, always.** `gh pr comment`, `gh pr edit --body`,
`gh issue create`, `pyrite create -b`: write the text with the Write tool and
pass `--body-file` / `"$(cat file)"`. Inline prose in a double-quoted shell
string executes every backtick as a command — on 2026-09-18 a comment
describing a recovery ran `git rebase` on `dev` in the main checkout (#123),
and three of the host's own commands were lost to the same quoting.

**Cleaning up an outside PR: one push.** When the maintainer has said a
contributor's PR is to be landed and the loop prepares it, do everything
locally first — rebase onto current `dev`, the single credited fixup, the
co-author trailers — verify (suite, `verify-red`, lint), and then push
**once**, `--force-with-lease=<branch>:<their current head>` with the SHA
read from `gh pr view N --json headRefOid` at that moment. Every push by a
non-owner to a first-time contributor's fork re-arms GitHub's approval gate,
so three pushes are three clicks on the maintainer's desk (#116 cost three,
#108 three, in one hour). Time the push for when the maintainer is present
to approve the run, and say in the comment that the run needs approval.
The `in-review` label is the lock: while it is set, nobody — including the
maintainer via "Update branch" — pushes to that branch; a fourth head
appeared under a worker mid-amend that way. **Co-author trailers use the
address from the contributor's own commit** (`git log -1 --format='%an <%ae>'
<their sha>`), never `<login>@users.noreply.github.com` — that form links
only for accounts created before mid-2017, and the fixup already on `dev`
for #116 credits nobody because of it.

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
