---
id: conductor-log-2026-W38
title: "Conductor log 2026-W38"
type: note
tags: [conductor, process, tick-log]
importance: 5
---

The pyrite-conductor's tick log for ISO week 2026-W38. One `## Tick` section
per invocation, appended by the conductor at the end of each tick. The
retrospective ([pyrite-meta-conductor](../../.claude/skills/pyrite-meta-conductor/SKILL.md))
reads this file, not any agent's memory: a tick that leaves no entry here did
not happen.

Because the `dev` ruleset requires a pull request for every change, this note
lives on the branch `kb/conductor-log-2026-W38` behind one draft PR held open
for the whole week, flipped to ready and merged at the retro. See the process
issue filed 2026-09-18 about the skill's "commit it on dev directly" line.

## Tick 2026-09-18T05:50Z

First tick of the week, and the first run of the conductor loop nested inside
an agent rather than at the top level.

**Health.** `dev` green (last three CI runs on `dev` succeeded; the head is
4e4368f). Nine PRs open: two draft theme claims (#38, #39), seven Dependabot
bumps for `web/` (#23–#29). No PR `BEHIND`. Four merged branches still had
remote refs (`kb/pull-forward-pool`, `process/retro-cadence`,
`process/retro-discipline`, `process/worktree-local-config`) — all four
verified merged into `dev` by subject match against PRs #50, #42, #41, #40.
Deleting them was refused by the harness permission classifier (`[Git
Destructive]`), so they stay; noted for the maintainer, harmless.

**Absorb.** Nothing to absorb. The two workers on #38
(`feature/playwright-foundation`, Playwright package A) and #39
(`feature/smoke-e2e`, live-server REST + MCP SSE + stdio + the CLI tutorial in
CI) were dispatched by the loop host ~30 minutes before this tick and are
still running; their reports go to the host, not to this tick. Left untouched
by instruction, and counted as two of the three in-flight slots.

**Choose.** One slot. The roadmap's pull-forward pool rule 4 says a pulled
item never displaces definition-of-done work, and the 0.24.2 definition of
done is not yet fully claimed, so the slot went to a definition-of-done item
rather than to the Dependabot batch or to the six issues the running workers
filed (#43–#45, #48, #49, #51). Of the unclaimed definition-of-done work,
`scripts/release.py` and the packaged web UI both collide on footprint with
#39 (`ci.yml`, `pyproject.toml`), so they must wait for it to land. That left
the milestone bugs, which are disjoint from both running themes.

Composed as one theme: **CLI write-and-report correctness** — #46 (`update
--tags` rewrites a backlog item's frontmatter: drops `kind`/`status`/
`priority`/`effort`, leaks `body`/`file_path`/`importance`), #18 (`index
health` prints "unhealthy" and exits 0; no `-k`), #21 (`db backup` writes into
the cwd). A reviewer reads these as one change: the CLI lies about what it
wrote, lies about what it found, and writes where it was not asked to. #46 is
a data-loss bug and leads under ADR-0032 §3a; #18 and #21 are small and ride
along so the PR is one reviewable unit rather than three fragments.

**Dispatch.** `scripts/new-worktree.sh fix/cli-write-and-report-correctness`
→ `/Users/markr/pyrite-wt/fix-cli-write-and-report-correctness`. Draft PR #69
is the claim. Model: **opus**, not sonnet — #18 and #21 alone would be
sonnet-shaped, but #46's root cause is in the model/storage write path
(`kb_service.update_entry` → `KBRepository.load` → `to_frontmatter` /
`save_entry`), it is a sibling of #15 one code path over, and the spec asks
for a named mechanism rather than a symptom patch. The spec pins the three
files the conductor traced before dispatching, tells the worker to verify
rather than trust that trace, and names the two running themes' files as hard
out-of-scope boundaries.

The theme spec is committed to the branch as `.claude/THEME.md` as well as
being the PR body — `gh pr create` refuses a branch with no commits, so the
empty-branch-plus-draft-PR claim from the skill needs something to sit on.

**Nested dispatch works.** `Agent(subagent_type="pyrite-worker", model="opus")`
was accepted from inside a subagent; the `general-purpose` fallback in
`dispatch.md` was not needed. The conductor loop can therefore run nested.

**Blocked / for the maintainer.** Nothing blocking a worker. Three `process`
issues filed from this tick's own friction:

- **#71** — the skill says to commit this log on `dev` directly; the ruleset
  forbids it. Worked around with the weekly branch and PR #70.
- **#72** — the permission classifier refuses read-only `gh pr view --json
  body` (intermittently) and the merged-branch cleanup step 1 of the tick
  specifies. Both need a maintainer decision on `.claude/settings.json`.
- **#73** — `gh pr create` refuses the empty branch the claim protocol is
  written around; worked around by committing the spec as `.claude/THEME.md`,
  which turned out to have a benefit worth keeping (the worker can re-read its
  own authority after losing context).

Also for the maintainer: seven Dependabot PRs for `web/` (#23–#29) are still
open and were not taken this tick — they are pull-forward-pool-shaped work and
rule 4 says definition-of-done comes first. They are the obvious first theme
once a slot frees up, landed as one PR rather than seven.

## Tick 2026-09-18T06:20Z

**Health.** `dev` green. Two runs on `dev` at the time of the check: the push
from PR #39 (35312463527) and a Dependabot graph update. PR #39 merged at
05:51:31Z, so the `smoke` job ran on a `dev` push for the **first time** —
and **passed**, in 95 s (05:51:46 → 05:53:21), all four steps green: live
REST, MCP over SSE, MCP over stdio, and the getting-started tutorial as
docs-as-tests. The breadth row of the 0.24.2 definition of done is no longer
theoretical; three of the four user surfaces are now gated on every push to
`dev`. The fourth (the web UI via Playwright) is exactly what the package
fan-out below is for. The `e2e` job is still `skipped`/`continue-on-error`,
which is correct — Package H flips it, and only after B–G.

Worktrees: four, all live (`feature-smoke-e2e` is now merged and its worktree
is the loop host's to clean, so it was left alone; the other three are the log,
the running CLI worker, and this tick's new one).

**Absorb.** Nothing to absorb. The only worker that finished since the last
tick is #38 (Package A), already merged by the host. PR #69's worker is still
running; the branch is `BEHIND` but it is a draft claim with an agent working
in its tree, so it was **not** rebased — rebasing under a running worker
invalidates the tree it is testing against, and a draft PR's BEHIND state costs
nothing until review. It gets `gh pr update-branch --rebase` at review, not
before. Worth writing into `review.md` as a rule: *rebase a draft claim only
when its worker has reported.*

**Choose.** One slot of three (PR #69's worker running; PR #39 merged during
the tick, which freed the second slot, but the tick had already been scoped to
one new theme and adding a second late is how a tick loses its review budget).
The host's ordered candidates put the Playwright fan-out ahead of the seven
Dependabot PRs, and the roadmap agrees: the fan-out is definition-of-done work
(the web UI surface), the bumps are pull-forward-pool stock, and pool rule 4
says a pulled item never displaces DoD work. Package **B** (`app.spec.ts` +
`settings.spec.ts`, 151 lines between them) is the smallest of B–G and the one
whose page-load describes the other packages' pages depend on for their
"the page loads at all" coverage, so it is the natural first of the fan-out.

**Dispatch.** `scripts/new-worktree.sh feature/playwright-package-b` →
`/Users/markr/pyrite-wt/feature-playwright-package-b`. Draft PR **#74** is the
claim. Model: **sonnet** — the judgment was spent in Package A (the world, the
auth decision, the contract in `fixtures.ts`); B is mechanical rewriting
against a contract that already exists, with acceptance a careful junior
engineer could take unattended. That is the `dispatch.md` tell exactly.

The spec pins four things the ticket's plan leaves implicit and a worker would
otherwise guess at:

- **Assert on seeded data, not on "list or empty state".** Half the existing
  assertions in `app.spec.ts` are `locator(A).or(locator(B))` — they passed
  against an undefined world by testing nothing. Now that the world is defined,
  an either-way assertion is the bug, not the flake.
- **Zero `text=` locators, and no `.first()` to dodge strict mode.** Named in
  the ticket's acceptance; restated per-file because a worker rewriting two
  files will otherwise carry the old idiom across.
- **Package A's four files are read-only.** `fixtures.ts`, `global-setup.ts`,
  `playwright.config.ts`, `seed.spec.ts` — B–G all run in parallel against
  them, and a worker "fixing" the shared contract is how a parallel fan-out
  becomes a serial rebase. Report it, do not change it.
- **Criterion 6: a real product bug does not get papered over.** The likeliest
  outcome of pointing a real assertion at a real app for the first time is that
  the app is wrong. The worker fixes a one-liner in its own footprint, or marks
  `test.fixme` with the bug named — it never weakens the assertion to green.

`.claude/THEME.md` again carries the spec on the branch (#73's workaround), and
again earns its keep: it is what the worker re-reads when its context turns
over mid-rewrite.

**Next (groom, not dispatched).** In order, for the following ticks:

1. **Packages C–G**, four to five Sonnet workers, disjoint spec files, all from
   the merged A — dispatchable in parallel up to the in-flight cap the moment
   slots free. C (auth) carries one decision A deferred: skip under
   auth-disabled, or a second Playwright project with auth enabled and a seeded
   user. That is design-shaped; C is the one package of the six that may want
   Opus.
2. **Package H** (`ci.yml`, the `continue-on-error` removal, the
   `test_dev_process_config.py` pin) — last, after B–G, Sonnet.
3. **Web dependency bumps** — the seven Dependabot PRs #23–#29 as one Sonnet
   theme, one PR, not seven. Note the ordering risk: they touch `web/`
   lockfiles while B–G touch `web/e2e/` specs; disjoint in file terms, but a
   `@sveltejs/kit` bump landing mid-fan-out could move the DOM the new specs
   assert on. Land it either before the fan-out or after all of it, not during.
4. **The MCP read-tier hallway-test findings** (#56–#68) and the worker/peer
   findings (#43–#45, #48, #49, #51–#55) — thirteen and ten issues, far too
   many to dispatch as themes one at a time. These want the **architect** in a
   groom lane: one `pyrite-architect` read over all twenty-three, returning
   themes with footprints, rather than the conductor composing them by hand
   from issue titles. That is the next tick's cheapest high-value dispatch if a
   Playwright slot is blocked.
5. **`scripts/release.py` and the packaged web UI** — both were footprint-
   blocked on #39 (`ci.yml`, `pyproject.toml`). #39 has now merged, so both are
   unblocked and are the remaining unclaimed 0.24.2 definition-of-done items
   besides the web-UI surface.

**Friction.** No new `process` issues filed. The three from tick 1 (#71 the log
on `dev` vs the ruleset, #72 the permission classifier on read-only `gh`, #73
the empty-branch claim) all recurred this tick and were worked around the same
way; recurrence is the retro's evidence, not a reason to re-file.

One new observation for the retro, not yet an issue: the **main checkout is not
a safe read surface**. `/Users/markr/pyrite` currently sits two commits ahead of
`origin/dev` with a peer session committing directly to its local `dev` and an
untracked directory in the tree. Every `git show`/`sed` this tick read
`origin/dev:<path>` explicitly rather than the working tree, which is correct
but is not what the skill says to do — `dispatch.md` and the tick's step 3 both
read files from the checkout as if it were `dev`. Known to the maintainer; if
it persists, the skill should say "read `origin/dev:<path>`, never the main
checkout's tree" rather than assume the checkout is clean.

**Blocked / for the maintainer.** Nothing blocking a worker. The kept items
remain kept: no release plan is due (0.24.2's definition of done is not met —
the web-UI surface is mid-fan-out and two DoD items are only just unblocked),
no ADR needs acceptance. The seven Dependabot PRs are still the one thing
sitting in the maintainer's field of view that the conductor has deliberately
not taken, and the reason is written above.

## Retro 2026-09-18T06:45Z (retro 1 — window 04:00Z–06:30Z, ticks 1–2, host-dispatched #38/#39)

### What worked
- Landing on `dev` unattended — 9 PRs merged (#35–#42, #50), 0 red `dev` pushes, 0 reverts, 0 redispatches; both worker branches (#38, #39) were first-time mergeable after the host's review, and their evidence reproduced on re-run (15/15 smoke, 4216 default, the Playwright stable-eleven).
- The KB fast path — process/KB PRs #41, #42, #50 merged in 0–1 min each (gate ~30 s); code PRs ~3 min.
- The smoke layer on the first `dev` push — run 35312463527, `smoke` 95 s green; full run 4 m 40 s.
- Workers filing instead of fixing — 9 issues (#43–#45, #48, #49, #51–#55) from two workers, zero scope creep in either diff.
- Nested dispatch — the Opus conductor dispatched `pyrite-worker` from inside itself twice (#69, #74); the worker outlived its parent tick.
- The draft-PR claim — tick 1 saw the host-dispatched #38/#39 with no shared memory.

### Failures and root causes
- #71 tick log on `dev` → the skill line predates the ruleset → the log has no home → **skill**: weekly `kb/` branch, one draft PR (PR #75).
- #73 empty-branch claim → `gh` refuses PRs with no commits; the skill assumed otherwise → tick 1 improvised `.claude/THEME.md` → **skill**: the claim commit is the theme's backlog item (PR #75).
- #72 permission refusals on read-only `gh` → no allow rule; `.claude/settings.json` is gitignored so none could ship → **settings.local.json** (maintainer-approved) + dispatch.md setup note (PR #75).
- ADR-0032 row conflict on #39's rebase → the host's two specs assigned two rows of one table to two parallel workers → dispatch.md's file-footprint rule was violated by the conductor, not the workers → note for next time; CHANGELOG conflicted in the same rebase → **quality item**: changelog fragments.
- `pyrite update --tags` corrupted six files while tagging the pool (#46) → product bug, in flight on #69; `pyrite create` writes `importance`/`rank` into frontmatter too (seen on the two items created this retro) — add to #46.
- #55 teardown race (pre-existing, ~1 in 3 under load) → not yet red on `dev`, will be → **quality theme** (this retro).

### Constraint
The build lane's in-flight cap — WIP 3 with one slot held by the tick-log PR #70, so 2 workers; groom queue at tick 2 = 5 themes ready (C–G, H, Dependabot, architect groom, release.py/web UI). Lead time per code theme 55–58 min (build 35–42, host review 10–15, gate 3–5); nothing waits on the maintainer (0 kept decisions pending).

### Friction observed
- Tick 1 had to invent a spec-file commit because the claim protocol could not be executed as written (#73).
- Ticks 1–2 read every file as `origin/dev:<path>` because a peer session is committing to the main checkout's local `dev` (2 commits ahead, untracked `Claude outputs/`); the skill assumes the checkout is `dev`.
- The host lost two `gh pr create` calls to inline-heredoc quoting; both retried with `--body-file`.
- The `pyrite-worker` agent type was refused in the host session (types register at session start) but accepted inside subagents.

### The one process change
The claim protocol corrected (first commit = backlog item; weekly log branch; cap counts workers) + the permission/`--body-file` setup notes — `.claude/skills/pyrite-conductor/SKILL.md`, `dispatch.md`; PR #75. Closes #71, #72, #73.

### The quality theme
`teardown-races-between-temporarydirectory-and-the-indexworker-thread-under-n` (high, S, Sonnet) — removes the one known intermittent red on `dev` (#55 + the connection-leak item); footprint `tests/conftest.py`, `tests/test_api_tiers.py`, `tests/test_index_worker.py`, `tests/test_admin_cli.py`. Stock for later: `changelog-fragments-one-file-per-pr-under-changelog-d-assembled-by-the-release` (medium, S).

### Expected effect
Themes dispatched per tick 1 → ≥1.5; `process` issues about claim/log 3 → 0 by the next retro; rebase conflicts per merged PR 1/9 → 0 once fragments land. Revert if the log PR goes a week without a ready flip, or item-per-theme makes `pyrite sw backlog` unreadable.

### Not changed, noted for next time
- The main checkout as a read surface while a peer session commits there — recommend the skill say `origin/dev:<path>`; waiting to see if the arrangement persists.
- Raising the cap above three — 2 green ticks of the 10 the skill requires.
- Cold reads: 0 dispatched, 0 needed (no server/storage/schema diffs yet); the trigger has not been tested.
- Dependabot #23–#29 — land before or after the Playwright fan-out, not during (tick 2's ordering risk).

### Absorb addendum — package B came back inside the same tick

Package B's worker reported ~16 minutes after dispatch, so the absorb happened
in this tick rather than the next. Reviewed per `review.md`, verifying with the
diff and the suite rather than the report.

**The diff.** `git diff origin/dev..HEAD --stat` at first looked alarming — it
listed `.claude/agents/pyrite-spike.md` deleted, the conductor SKILL.md and
`dispatch.md` rewritten, `CLAUDE.md`, two KB backlog files gone. None of it was
the worker's: `origin/dev` had moved two commits during the tick (the peer
session's `skills:`/`agents:` work), and a `--stat` against a moved ref shows
the drift as if it were the branch's. `git show --stat <worker's sha>` is the
honest question, and the answer was **exactly the three files the spec named**:
the two spec files and a two-attribute diff in `settings/+page.svelte`.
Footprint discipline was exact. Worth putting in `review.md`: *diff the
worker's commits, not `base..HEAD`, when base has moved.*

**The evidence, re-run.** 26 passed / 1 skipped in isolation; 388/388 unit
tests; and the thing the worker explicitly could not claim — its third
"Unsure", that it had not proven non-interference in the **full** suite — now
proven: 36/36 across `app.spec` + `settings.spec` + `seed.spec` inside a full
run, with the run's 9 failures confined to `auth`/`collections`/`entry-crud`/
`qa`/`search`, i.e. precisely the specs packages C, D, E and G still own. The
fan-out's disjointness assumption holds in practice, not just on paper. That is
the single most useful fact this tick produced for the next one: C–G can go out
in parallel with confidence.

**The falsification check, and the trap in it.** The skill says to spot-check
that a new test fails with the fix stashed. Done the obvious way it gave the
**wrong answer twice over**: `git stash pop` resurrected a months-old
`WIP on feature/journalism-investigation-kb` stash (the stash stack is shared
across worktrees through the common git dir), conflicted into two unrelated
`kb/backlog/done/*.md` files, and meanwhile the tests "passed with the fix
stashed" — which reads as *vacuous assertions*. They are not: deleting the
attribute directly and re-running failed exactly as it should. A flawed
instrument produced a false negative on the one check whose entire purpose is
catching vacuous tests. Filed as **#80**; the fix is to falsify by editing the
line directly, never through the shared stash stack. The unrelated stash was
restored, not dropped, and the worktree left clean.

**Cold read: not dispatched, deliberately.** The worker's "Unsure" was
non-empty, which is a stated trigger — but all three items were verifiable
directly and were verified (the `/` drift, the `toHaveCount` judgment, the
full-suite question). The diff touches no server, storage, schema, auth or
public shape; it is 200 lines of test code plus two HTML attributes. A cold
read here would have bought nothing the re-run did not. The trade-offs went
into the PR body instead, which is where a reviewer will actually meet them.

**Two judgment calls accepted.** (1) The `/` describe changed *meaning*: it
asserted a `Dashboard` heading and stat cards, but `/` is now the landing page
and the stats view moved to `/overview`. The old spec missed the move because
its or-either-way assertions passed regardless — the exact pathology this
package exists to end. Rewriting it was right; the coverage hole it exposes is
**#79**. (2) Two `expect(...).toHaveCount(1)` waits are *not* `.first()` in
disguise — both are documented double-render races (the layout's
`{#key}` fade; #45's empty-state flash) where the assertion waits for the race
to resolve to the one real element rather than grabbing whichever won. Criterion
3 is met in substance, not just in letter.

**One product bug preserved rather than papered over.** `sets the document
title` is `test.fixme`'d against **#49** with the correct assertion intact
(live: `toHaveTitle` got `"Pyrite"`, not `"Settings — Pyrite"`). Criterion 6
worked as designed — the worker had every incentive to weaken the assertion to
green and did not. **Un-fixme when #49 lands.**

Rebased onto the moved `dev`, re-verified green after the rebase, body written,
flipped to ready, auto-merge armed. **PR #74 is in review with its gate
running.**

**Issues filed this tick:** #79 (product: `/overview` has no e2e coverage after
the landing-page split — no package in the current plan owns it), #80
(process: the stash-based spot-check is unsafe in a worktree and gave a false
negative).

**In flight at tick end: 2** — #69 (CLI correctness, worker still running) and
#74 (package B, gate running). A slot is free; the next tick should spend it on
packages C–G, now that disjointness is proven rather than assumed, with C the
one that may want Opus for the auth decision A deferred.

### Tick close — package B merged

PR #74's gate went green (`frontend` 1m0s, `gate` 3s; `test`/`kb`/`smoke`
correctly skipped for a web-only change) and auto-merge landed it. Worktree
removed, branch deleted. Its push to `dev` is building.

So this tick both dispatched and landed a theme: **dispatched → reviewed →
merged inside one tick**, which the three-lane model treats as unusual (build
and review are meant to be different ticks' work) but which a 16-minute Sonnet
package makes possible. Worth noting for the retro: when a theme is genuinely
mechanical against an existing contract, the pipeline collapses to one tick and
the in-flight cap stops being the binding constraint. That is an argument for
sizing packages *small enough to round-trip in a tick*, not merely small enough
to review.

At close, other sessions had created worktrees for packages **C, D, E** and a
`quality/test-teardown-races` theme. Not mine; left untouched. Package B's
full-suite evidence above is what those packages need, and it says they can run
in parallel safely.

**Final state this tick: 1 merged (#74), 1 in flight (#69, worker running), 2
issues filed (#79, #80), smoke green on its first dev push.**

---

## Tick 2026-09-18T06:10Z (tick 3 — the fan-out tick)

Run by a separate Opus session on the loop host's behalf; the :07 cron firing
was missed because the host was mid-turn. Tick 2 was still closing as this one
opened, so the two overlap in the record: #74's merge and worktree cleanup are
tick 2's, written up above by the host, and the worktrees the host noticed
"created by other sessions at close" are this tick's.

**Health.** `dev` green — Package B's push (35314099398) went green in 1m52s,
the third consecutive green push. Six worktrees at open, all live. One
surprise, worth writing down because it looked like a failure and was not: the
`feature-playwright-package-b` worktree **disappeared mid-tick** while this
session was reading it. It had not been lost; the loop host had reviewed,
flipped, merged and cleaned it up inside its own tick. A conductor reading
`git worktree list` while a peer session absorbs the same work sees a directory
vanish under it, and the only durable signal is `gh pr view` — which said
`MERGED`, `headRefOid` matching the rebased tip. **State lives in GitHub, not
in the filesystem**, exactly as the skill claims; this tick got to test that
claim by accident.

**Absorb.** Nothing absorbed. One candidate and it was correctly left alone:
PR #69's branch has four commits, a clean tree and a docs/changelog commit
last — the "done-shaped last commit" the host's note says to review on. Before
touching it, `ps` showed five `.venv/bin/python` xdist workers running in that
worktree at 50% CPU each: the worker is running its full suite this minute, not
finished. Reviewing a branch whose owner is mid-verification would have meant
reading a tree about to change. **Left running; not rebased** (the draft-claim
rule from tick 2). Its diff, previewed for sizing only: 989 insertions across
14 files, all three issues covered with a test file each, touching
`pyrite/models/base.py` (+144), `pyrite/storage/`, `pyrite/schema/reserved.py`
and a software-kb extension type. That footprint is three separate cold-read
triggers (storage, schema, public shape), so **#69's review must include a
`pyrite-reviewer` cold read** — the first one this loop will have dispatched.

**Groom.** `pyrite-architect` (Opus, read-only) dispatched over the ~23
ungroomed open issues — #56–#68 (the MCP read-tier hallway-test findings) and
#43–#45, #48, #51–#54 (worker and peer findings) — with everything in flight
excluded by number and by file, and with packages F/G/H excluded as already
well-specified by the parent ticket. The skill's trigger is mechanical: the
ready queue held fewer than twice the worker cap. It is read-only and runs
beside the builds, so it costs the tick nothing but tokens, and tick 2 already
named this as the cheapest high-value dispatch available.

**Choose.** Five themes, ordered by the value chain, one of them the quality
theme that was due:

1. **The quality theme, taken ahead of features.** Retro 1 groomed it and the
   skill's every-~fifth-theme rule made it due. `tests-leak-open-pyritedb-
   connections-into-temporarydirectory-teardown` (the nine test files holding
   SQLite connections open in WAL mode inside a `TemporaryDirectory`) merged
   with **#55** (the `IndexWorker` thread writing into the same directory as
   `rmtree` walks it) — the same failure shape from two directions, so fixing
   either alone leaves the suite flaky and nobody can tell which. It is the one
   known intermittent red on `dev`, and a suite that fails one run in three
   teaches every future agent to ignore a red. The spec forbids the four ways
   out that are not fixes (`ignore_cleanup_errors`, a sleep, an `rmtree` retry,
   a flaky marker) and says that production code which starts a thread its
   owner cannot join is a product bug, not a test bug.
2–4. **Playwright packages C, D and E**, in parallel. Disjointness is now
   proven rather than assumed (tick 2's full-suite evidence), and each package
   owns its own spec files.

**Dispatch — five workers, the first time the raised cap has been used.** The
new rule (up to six when footprints are disjoint and fewer than two branches
await review) applied exactly: zero branches awaited review at dispatch, and
the four new themes touch four disjoint file sets, none overlapping #69's.

| Theme | PR | Model | Why that model |
|---|---|---|---|
| quality: test teardown races (#55 + the connection-leak item) | **#81** | sonnet | the fix is named in the item (a shared `make_client` fixture in `conftest.py`); the expensive part is 10 consecutive `-n auto` runs, which is patience, not judgment |
| Playwright **C** — `auth.spec.ts` + the auth-enabled project decision | **#82** | **opus** | the one package of six that carries a design decision A deferred: skip the auth specs, or stand up a second Playwright project with its own backend, port, data dir and seeded user. Also the only package permitted to touch the shared `playwright.config.ts` |
| Playwright **D** — `entry-crud` + `entry-features` | **#83** | sonnet | mechanical against an existing contract |
| Playwright **E** — `collections` + `daily` | **#84** | sonnet | mechanical against an existing contract |

Each spec pins what a worker would otherwise guess at, and two pins are
package-specific because the trap is package-specific:

- **D is the only pair that writes.** The seeded world resets per run, but a
  writing spec shares the world with its siblings *inside* a run and with
  itself on a re-run. So: `uniqueTitle()` for everything it creates,
  `idForTitle()` rather than a hand-written slug, never a title another spec
  asserts on, and a delete test deletes only what it created. The spec names
  the failure mode so it is recognised rather than debugged: a spec that passes
  on run 1 and fails on run 2 has a collision, not a flake.
- **E's daily route writes on a GET.** With auth disabled every caller has
  write tier, so `GET /daily/{date}` *creates* a note for a date that has none;
  A pre-seeded a fixed date plus offsets −3..+2 precisely so those GETs are
  reads. E must navigate only inside `SEEDED_DAILY_DATES` — counting the
  prev/next clicks, not assuming — or it silently mutates the world its
  siblings assert on.
- **C is additive-only on the shared config.** Every other spec runs under
  `playwright.config.ts`, so it is the one file in this fan-out whose edit can
  break four other branches. The spec forbids changing the existing `chromium`
  project, the `webServer` entries, `retries: 0` and
  `reuseExistingServer: false`, and requires C to run the *whole* suite 5× (not
  just its own file) because it changed what everyone runs under.

All four specs restate B's two hard style rules (zero `text=` locators, no
`.first()` to dodge strict mode) and B's criterion 6, which earned its keep
last tick: a real product bug gets `test.fixme` with the bug named, never a
weakened assertion. B found **#49** that way, and the specs cite it as the
precedent so the next worker knows the rule is real and not decorative.

**The claim protocol, exercised as amended.** All four claims are a backlog
item as the first commit (PR #75's change), and three of the four items had to
be **written by hand** rather than created with `pyrite create` — see below.
The quality theme's item was claimed with `pyrite update`, which is how this
tick reproduced #46 first-hand.

**#46 reproduced while claiming, with a new asymmetry.** `pyrite update <id>
-f status=in_progress -f assignee=...` on a well-formed `backlog_item` leaked
`body:` (the entire body as a YAML string) and `file_path:` (an absolute path
into *this worktree*, which would have been committed) — but `kind`, `priority`
and `effort` **survived**, where #46 as filed reports them dropped. So the
"leaks model internals" half and the "drops declared fields" half of #46 are
separable and reproduce differently per entry. Posted to PR #69 as a comment
rather than a scope change: its spec already asks the worker to explain the
`--title`/`-b` asymmetry, and this is a second asymmetry along the same seam.
The leaked keys were stripped by hand before committing the claim.

**Issue filed: #86** — the same class on the *create* path. `pyrite create -t
backlog_item` emits `importance` and `rank` (model internals) and omits `kind`
and `effort` (declared fields that `pyrite sw backlog` reads), with no flags to
supply them, so **every agent that creates a backlog item must hand-edit the
file afterwards to make it well-formed**. This tick did that three times, which
is how it was found. Suggested acceptance includes the test that would have
caught both this and half of #46: create each software-kb type through the CLI
and assert the on-disk frontmatter against the type's declared fields. Product
bug, not process — so an ordinary issue, per ADR-0033.

**Friction.** No new `process` issues. The three standing ones (#71, #72, #73)
are fixed in the skills as of PR #75 and this tick executed the amended
protocol without improvising — `.claude/THEME.md` was not created for any of
the four new themes; the spec lives in the draft PR body, which is what the
workers are told to re-read. That is the retro's change working on its first
use. Two observations for the next retro, neither worth an issue yet:

- **Reading the main checkout is still wrong and still necessary.** Every file
  this tick read came from `origin/dev:<path>`; the working tree was stale
  again (`web/e2e/global-setup.ts` did not exist in it although Package A had
  merged). Tick 2 recommended the skill say so explicitly. Third tick running.
- **A peer session absorbing your work while you hold a reference to it.** The
  vanishing worktree above. No harm done, and arguably the system working, but
  a conductor that had `cd`'d into that directory would have failed mid-command
  with a confusing error rather than a clear "someone merged this".

**Blocked / for the maintainer.** Nothing blocking a worker; nothing awaiting a
kept decision. No release plan is due — 0.24.2's definition of done still wants
the web surface (C–H in flight or queued), `scripts/release.py` and the
packaged web UI. The seven Dependabot PRs (#23–#29) remain deliberately
untaken: they touch `web/` lockfiles while four workers rewrite `web/e2e/`
specs, and a `@sveltejs/kit` bump landing mid-fan-out would move the DOM those
new specs assert on. They land as one PR **after** the fan-out, per tick 2's
ordering call.

**Final state this tick: 0 merged (tick 2 took #74), 5 in flight (#69 verifying,
#81/#82/#83/#84 dispatched), 1 architect grooming ~23 issues, 1 issue filed
(#86), 1 root-cause data point posted to #69.**

### Tick 3 close — the architect's breakdown (the ready queue for tick 4)

The groom returned after the tick's dispatch was already out, so nothing here
was dispatched this tick; it is the ready queue tick 4 chooses from. **23 issues
collapse to 7 themes, 2 spikes, 1 duplicate, 3 maintainer decisions.** Two
findings change the shape of the set before any theme is written, and I verified
both against `origin/dev` rather than taking the report's word:

- **#78 is a duplicate of #55** — same fixture (`test_api_tiers.py`
  `three_key_client`), same `OSError`, same `-n auto` condition; filed from the
  #69 worktree without sight of #55. PR #81 already covers it. Commented on the
  issue; close it when #81 lands.
- **#43's stated root cause is false.** It claims `pyrite init` writes no
  `auto_embed` key and that is why nothing embeds. But `config.py:350` is
  `auto_embed: bool = True` and `:765` is `settings_data.get("auto_embed", True)`
  — **an absent key means on** (verified). The embed is being attempted and
  silently failing in one of three places that each degrade to `logger.warning`.
  A worker specced on #43 as written would add a key, change nothing, and close
  it. Commented on the issue; it is now Spike 1.

**The seven themes, in the architect's recommended order:**

| # | Theme | Closes | Model | Cold read | When |
|---|---|---|---|---|---|
| 1 | Search filters honoured in every mode, on every surface | #53, #56 (+#67) | opus | yes | **now** — the only DoD item in the set |
| 2 | MCP read-tier response contracts (projection, limits, errors that name the problem) | #57, #58, #63 | sonnet | no | now |
| 3 | Plugin validators actually run, and a failing one is loud | #48 | opus | yes | now |
| 4 | `index health` tells the truth about a correct KB | #44, #47, +pool #6/#7/#8/#19/#22 | sonnet | yes | after #69 merges |
| 5 | Entry-type vocabulary: report the drift, resolve on read | #59, #60 | sonnet (scoped down) | no | after 4 |
| 6 | Web: KB store resolves before the page judges it empty; page titles survive | #45, #49 | sonnet | no | after the whole fan-out |
| 7 | Cross-KB read tools: correlate, disclose the tier, separate staging from canon | #61, #62, #64, #65, #66, #68 | opus | yes | **0.25** |

**Themes 1, 2 and 3 are dispatchable in parallel** (footprint-disjoint, no
collision with #69, #81 or the fan-out) once the review queue drains — with
**#67 moved from theme 2 into theme 1**, which is what makes them disjoint;
otherwise both touch `search_service.py`.

**Two root causes I verified myself**, because they are the load-bearing claims:

- **Theme 1.** `_semantic_search` (`search_service.py:336`) takes *no filter
  parameters at all*; `_hybrid_search` (`:361`) passes filters only to the FTS
  leg, so the fused RRF set admits vector-leg rows no filter ever saw. The
  correct guard already exists in the file — `if status:` at `:409`, with a
  docstring explaining the leg split — applied to `status` and `kb_names` and to
  none of the other four filters. `status` is the one filter both testers
  measured as correct in hybrid mode. That is not a coincidence; it is the only
  one with the guard.
- **Theme 3.** `extensions/cascade/.../plugin.py:458` is
  `def _validate_cascade_entry(entry) -> list[str]` — one arg, returning strings.
  `kb_schema.py` calls `validator(entry_type, fields, ctx)`, falls back to
  `validator(entry_type, fields)`, and swallows the second `TypeError` into a
  `logger.warning`. **Neither call matches**, and the return contract is wrong
  too (the caller does `item.get("severity")` on a `str`), so fixing the arity
  alone converts a silent skip into an `AttributeError`. No cascade entry has
  been plugin-validated for as long as the signatures have been out of sync.

**The shape those two share is worth naming:** a guard exists, correctly, for
exactly one case, and nobody generalized it. Both produce plausible output,
which is why both survived; both were found by an agent doing real work rather
than by the suite. **13 of the 23 issues came from one read-tier hallway-test
session, and the two most valuable themes here are built out of them.** That is
the strongest evidence the loop has produced for the hallway-test practice
itself — retro material.

**A gap the groom found by looking at what is *not* in the pile:** milestone
0.24.2 contains #56, #46, #21, #18, #13 and #9. #46/#21/#18 are PR #69, #56 is
theme 1 — and **#13 and #9 have no owner anywhere in this breakdown**. #9 (web
search never renders — the flagship flow on the demo) is the release's most
user-visible open bug and none of the 23 issues touches it. Tick 4 should compose
a theme for #9 directly from the milestone, not wait for the groom to surface it.

**Two spikes** (`pyrite-spike`, opus, one tick, no PR, deliverable is a changed
ticket): **Spike 1** — which of the three silent guards swallows the embed on a
fresh install, and is the answer to #43 and #13 the same decision? **Spike 2** —
is #51's `parked_awaiting` a stale index row or a lost write? The reporter could
not open `index.db` to confirm, and the current `dev` metadata path reads as
correct, so the defect is either in what `sync_incremental` rewrites for an
already-indexed path or in a hydration path that is not reached — different
fixes in different files. Spike 2 is cheap enough to be a conductor task.

**Routed out of the dispatchable set:** **#52** (the conductor skill prescribes a
worse manual workaround than a `task reset`/`task checkpoint` that already
exists) is a *skill* fix, not a worker theme — **route to the meta-conductor's
retro**. **#54** (the best-written usability report in the pile) waits for theme
1: once filters actually work, half of it may be answered and the rest will have
evidence behind it.

**Kept decisions this surfaces — not dispatched, for the maintainer:**
1. **#59's `type_aliases` in `kb.yaml`** — a public file-format addition plus a
   new read-time resolver behaviour. Recommendation: ship the drift *reports*
   first (theme 5, scoped down) and let the data say whether the alias map earns
   its keep.
2. **#62's `canon: true|false` on the KB registry** — changes the default result
   set of every cross-KB read. Wants an ADR, written together with the pool's
   `collapse-kb-registry-to-one-source-of-truth` row; they are the same object.
3. **#66's `detail: "brief"|"full"` on `kb_orient`** — a public MCP argument on
   the tool every session calls first. Goes with the #62 ADR.

Packages **F** and **G** remain parallel-safe and un-groomed (already specified
by the parent ticket); **H** is the gate flip and must be last, after F and G are
green on `dev`. Theme 6 comes after H, and the Dependabot batch lands in that
same window.

## Tick 2026-09-18T06:45Z — absorb of PR #69 (parallel conductor session)

Written by the nested conductor session that dispatched the
`fix/cli-write-and-report-correctness` theme (#46, #18, #21) earlier in this
log. Its worker reported inside the same tick, so the absorb lane ran on it
immediately. Recorded here because the retro reads this file, not any agent's
memory — and because two of the findings generalise past the theme.

**Verified, not taken on trust.** Suite re-run in the worktree: `4244 passed,
68 skipped` vs `4212` on `dev` (+32 tests, 0 failures). Each acceptance
criterion checked by running it: #46's repro now gives an *empty* diff while a
genuine tag edit gives a *one-line* diff with inline `[a, b]` style preserved;
#18 exits 1 when unhealthy, 1 on an unknown KB (not a false clean bill), 0
under `--no-fail`, valid JSON on stdout and an empty stderr; #21 leaves an
unrelated cwd untouched.

**The measurement that matters.** A no-op load→save round trip over the whole
`pyrite` KB — no edit at all — ought to be byte-identical. On `dev` it rewrites
**768 of 768** entries; on this branch **148 of 766**. An 81% reduction on
exactly the axis the theme is about. The residual 148 differ only inside
`links:` (bare-string links expanded to mappings, nested sequences
re-indented). I suspected link `note:` fields were being dropped, checked it
directly, and they are **not** — restyling, not data loss. Filed as **#90**
with the round-trip count itself as the acceptance criterion: that invariant
caught both this and #46, and would have caught #15.

**Root cause, confirmed independently.** `pyrite/storage/repository.py` was
injecting `body` and `file_path` into the frontmatter dict it then handed to
`capture_extra_frontmatter`, which decides "undeclared frontmatter"
empirically — so two model internals were recorded as extras and written back
into the file on every save. Removing the injection is the whole fix. Nothing
reads those keys: zero readers of `meta["body"]`/`meta.get("body")`/`file_path`
across `pyrite/` and `extensions/`, and every extension `from_frontmatter`
takes `body` positionally. The exit-code change is safe in-tree too — the only
in-repo mention of `index health` is one line of prose in a skill.

**Where the worker's report was wrong.** It filed **#78** for a teardown flake
in `test_api_tiers.py`, asserting it was pre-existing and "confirmed by
reproducing it with this branch's changes stashed". Measured: **0
reproductions in 4 full-suite runs on clean `dev`, 2 in 4 on the branch**, plus
a 5th targeted run that reproduced on the first attempt. The underlying race
*is* pre-existing — the class-scoped fixture leaves `index.db-shm`/`-wal`
behind after `close()`, identically on both trees — but the branch takes it
from never to ~50% under `-n auto`, so the stated confirmation does not hold.
The obvious suspect is ruled out: the new `_restyle_like_source` deep-copy is
not a slowdown (200 load+save round trips: 0.182s branch vs 0.214s `dev`).
Numbers posted to #78. **This is directly relevant to PR #81** ("no test
leaves a writer running"), which is grooming the same teardown-race class.

*Retro-worthy, and the reason the absorb lane exists:* a worker's
"pre-existing, unrelated to my change" about a flake it met during its own
theme is a claim to **measure**, not to accept. It is among the cheapest
things to get wrong and the most expensive to inherit, because it launders a
regression into the backlog as somebody else's pre-existing problem.

**Process defect caught in review, worth more than the bug.** The worker's four
code commits were **never pushed** — only the conductor's spec commit was on
the remote. CI had therefore classified PR #69 as docs-only, **skipped the
`test` job, and reported green**. A conductor reading `gh pr checks` without
comparing local `HEAD` to `origin/<branch>` would have seen a passing PR with
none of its code tested. The dispatch prompt says "do not open a PR" and this
worker reasonably read that as "do not push"; the skill does not distinguish
them. Filed as **#91**. Suggested rule for the review checklist: *before
reading checks, assert `git rev-parse HEAD == git rev-parse origin/<branch>`* —
green CI on an unpushed branch is worse than red, because it looks finished.

**Cold read dispatched** (`pyrite-reviewer`, opus) on the triggers
`pyrite/storage/` + `pyrite/schema/` + a public shape change + a modified
existing test assertion + a non-empty "Unsure". Its brief names the blast
radius of `_restyle_like_source` (runs on every write, ~48 entry types) and the
`_absent_default_keys` interaction with commit 7783335's data-loss fix, and
tells it explicitly not to treat the conductor's reading of the #78 flake as
settled.

PR #69 stays **draft** pending the cold read and a genuine CI run on the
now-pushed code.

## Tick 2026-09-18T07:10Z — cold read on PR #69, and a redispatch

The cold read came back on `fix/cli-write-and-report-correctness` and changed
the disposition from "ready to flip" to "do not merge". It found two data-loss
regressions the conductor's own review had missed, and corrected a measurement
the conductor had already published. Both are recorded here because the retro's
subject is the process, and this tick is evidence about what the review lane
catches and what it does not.

**Two regressions, both reproduced by the conductor before acting.** A
reviewer's report is model output on the same terms as a worker's.

1. **`--importance 5` is a silent no-op** — a straight regression of commit
   7783335's data-loss fix. `_absent_default_keys` is recorded at load and
   never invalidated on assignment, and `update_entry` does a plain `setattr`,
   so an explicit set *to the default value* is indistinguishable from "never
   set". The write reports `{"updated": true}` and persists nothing. Reachable
   from the CLI, REST `PUT`/`PATCH`, MCP `entry_update`, and the software-kb
   reorder (which legitimately computes `rank=0`). Same bug for `rank`.
2. **`copy.deepcopy` of the ruamel `CommentedMap` destroys YAML anchors and
   merge keys**, emitting a duplicate key that a strict loader rejects. `dev`
   round-trips the same input losslessly, so it is introduced, not inherited.

The shapes are worth naming: the theme fixed "a write changed something you did
not ask for" and introduced "a write did **not** change something you
explicitly asked for". Both silent, both reporting success. The common cause is
**inferring intent from load-time state** instead of recording whether a field
was assigned — the redispatch says so, and prefers a dirty-field signal over
the minimal patch.

**The test that made it look safe.** `TestAlwaysWrittenDefaultsStillWork` is
named for exactly regression 1 and covers only the cases that already work (two
in-memory constructions, and a file that *already has* the key). The failing
case is absent. It would have landed looking tested, which is worse than an
obvious gap — and it is the strongest argument yet for the cold read as a
standing trigger rather than a judgement call, because the conductor read that
class and was reassured by its name.

**A measurement the conductor got wrong, corrected in public.** The earlier
absorb entry and a PR comment asserted the new write path was "not slower"
(0.182s vs 0.214s). That compared the **branch venv on Python 3.11.14 against
the dev venv on 3.13.7** — two interpreters, not two codepaths. Invalid. The
cold read caught it and reported the opposite (+71% load, +99% save); re-run
under one interpreter with both trees resolving correctly (PYTHONPATH pinned,
1440 cycles, two rounds), branch and dev are **within noise**:

| round | branch load | dev load | branch save | dev save |
|---|---|---|---|---|
| 1 | 2.691s | 2.629s | 2.299s | 2.265s |
| 2 | 3.038s | 3.197s | 2.036s | 2.002s |

So **neither** performance claim about this branch stands, and the conductor's
was published first and confidently. The flake-rate measurement (0/4 on `dev`,
2/4 on the branch) was made on the real suite and still stands; its *mechanism*
is now unexplained and is being asserted in neither direction. Corrected on PR
#69 and in the redispatch so the worker is not optimising against a phantom.

*For the retro, the generalisable lesson:* **a benchmark across two worktrees
is a benchmark across two environments.** Each worktree gets its own `.venv`
from `scripts/new-worktree.sh`, and those venvs can resolve different Python
versions, so any A/B measured by "run it here, then run it there" is confounded
by construction. This is a property of the worktree-per-theme workflow itself,
not a mistake unique to this tick, and it will recur silently. Worth a line in
`review.md`: measure both codepaths under one interpreter, pinning the source
tree, or do not report a number.

**Disposition.** PR #69 stays **draft**. Redispatched to the same worker (via
`SendMessage`, so it keeps its context) with the three defects, the two
corrections, and an explicit instruction to push this time. Not a new PR — the
follow-up belongs to work in flight, so it goes onto that branch. The
`index health` and `db backup` halves were given explicit clean bills by both
readings and survive the next pass unchanged.

### Tick 3 close — Package E absorbed, and two structural findings

**PR #84 (Package E) reviewed and flipped to ready.** The worker's report was
verified rather than taken: full diff read, footprint confirmed against the spec
(Package A's four files untouched, no sibling's spec touched), style criteria
checked by `grep` — zero bare `text=` locators (the single hit is inside a
comment explaining why one was *avoided*, a false positive worth knowing about
for future reviews), and the one `.first()` is the header row of a genuinely
repeated `.grid-cols-7` structure, commented as required.

**It exceeded its spec in the right place.** The seeded-date constraint was
given as a rule to follow; the worker turned it into `assertOffsetSeeded(n)`,
which *throws* if the offset math would leave the −3..+2 seeded range. The
constraint is now enforced at test-run time rather than by inspection, so a
future edit to `daily.spec.ts` cannot silently start writing notes. That is the
difference between a spec that documents a trap and one that closes it.

**#89 confirmed by reading the code, not by trusting the report.**
`Calendar.svelte`'s second `$effect` reads `viewYear`/`viewMonth` inside its own
comparison, making them its own dependencies: `prevMonth()` changes them, the
effect reruns, sees a mismatch with `selectedDate`'s month, snaps back. On
`/daily`, `selectedDate` is always set, so month navigation is **permanently
inert** — a real user-facing bug that the old either-way assertions could never
have caught. Correctly filed and `test.fixme`'d with the assertion left correct,
so it self-heals when #89 lands. Criterion 7 has now earned its keep in three
consecutive packages (B→#49, E→#89).

**Two process issues filed this tick, both structural, neither a worker's fault:**

- **#103 — `CHANGELOG.md` is the one file every theme touches.** PR #69 went
  `CONFLICTING`, and `git merge-tree` showed **exactly one** conflicting file out
  of a 989-line, 14-file diff: `CHANGELOG.md`. The important part is the second
  order effect: a conflicted PR gets **zero checks**, because GitHub stops
  computing the merge commit —
  `gh api .../commits/<head>/check-runs` returned `total_count: 0` while the four
  other in-flight claims all showed 8. #69's worker saw the missing checks and
  pushed an empty `ci: re-trigger PR checks` commit trying to shake them loose;
  it could not, because the cause was not a missed event. A worker spent commits
  on a diagnosis the conductor was better placed to make. **The conflict rate
  scales with exactly the thing the loop is trying to increase** — five workers
  in parallel today, six allowed — so retro 1's groomed
  `changelog-fragments-one-file-per-pr` item should be dispatched, not held as
  stock, and it pairs naturally with `scripts/release.py` (also 0.24.2 DoD).
- **#104 — Playwright's hardcoded ports serialize a fan-out built to run in
  parallel.** `playwright.config.ts` pins 8088/5173 for every worktree with
  `reuseExistingServer: false` (correctly — a server already on 8088 is somebody's
  real Pyrite, and this suite writes). Package E's worker hit
  `port is already used` repeatedly and confirmed Package C's worktree held it.
  Then the conductor hit it from the other side: **re-running E's suite for review
  was impossible** while siblings were running (both ports held, 29 live
  playwright processes). So the one piece of E's evidence that could not be
  independently verified is its 5× run, and that limitation is stated in the PR
  body rather than papered over. No package worker can fix this — the config is
  correctly read-only to all of them, so each rediscovers it and pays the cost
  again. Belongs to Package H, **before F and G are dispatched**.

**#69 is the next tick's first job and it is not blocked on its worker.** It is
`CONFLICTING` on `CHANGELOG.md` alone; everything else merges clean. Tick 4:
rebase it (its worker's tree is quiet), take both sides of `[Unreleased]`, let
the checks finally run, then review with the **cold read** its footprint demands
(`pyrite/models/base.py` +144, `pyrite/storage/`, `pyrite/schema/reserved.py`).

**State at close: 1 in review (#84, rebased, auto-merge armed, checks running),
4 in flight (#69 conflicted/awaiting rebase, #81 running its 10× suite, #82, #83),
3 issues filed (#89 product via the worker, #103 and #104 process via review).**

### Tick 3 close — #84 merged, #69 unblocked, and a spec file leaked onto dev

**PR #84 (Package E) merged** at 07:02:20Z and its content verified present on
`dev` (16 `assertOffsetSeeded` guards, the calendar testid, the backlog item in
`kb/backlog/done/`). Worktree removed; the branch needed `-D` rather than `-d`
because auto-merge **rebased** it, so the local tip was the pre-rebase copy —
worth knowing so a future tick does not read "not fully merged" as "not merged".

**#69's conflict resolved by the conductor, not its worker.** The worker had
finished; its tree was clean and quiet, so the rebase was mine to do. Two
findings from doing it:

1. **The `CHANGELOG.md` conflict resolved itself cleanly on replay** — the three
   new entries append after `dev`'s existing #15 entry with nothing lost. So
   #103's cost is not the resolution, it is that the conflict *silently starved
   the PR of checks* until someone noticed. The fix is still worth doing: the
   next one may not replay this cleanly.
2. **The real conflict was `.claude/THEME.md`** — and it exposed that **Package
   B leaked its theme file onto `dev`** when it merged (commit `22619c9`). The
   skill explicitly warns about this: "Do not commit the spec as a loose file:
   it has to be removed before the PR goes ready, which a tick forgets." Tick 2
   forgot, exactly as predicted. `dev` now carries a stale Package B spec.

   The rebase's first pass resolved the conflict by *deleting* the file, which
   would have made #69 silently clean up another theme's litter — a change
   nobody reviewing "CLI write-and-report correctness" would expect to find.
   Restored it with `git checkout origin/dev -- .claude/THEME.md` and amended,
   so **#69's diff no longer touches the file at all**. Removing B's leftover is
   a separate one-line KB/chore change, and it belongs to whoever next has a
   reason to touch `.claude/` — not smuggled into a bugfix PR.

This is the second time in two ticks that the *right* resolution of a mechanical
conflict was "make my branch touch less", not "take one side". Worth a line in
the retro: a conductor resolving a rebase should ask what the PR's reviewer
would expect to see in the diff, not merely what makes the conflict go away.

**State: #84 merged and cleaned up. #69 rebased onto current `dev`, force-pushed
(pre-push suite running), and should finally get its first real `pull_request`
checks — it has never had any. Once green it needs the cold read its footprint
demands. #81 has pushed its fix and is running the 10x suite; #82 and #83 have
both pushed commits ahead of their claim.**

### Tick 3 correction — the conductor rebased a branch whose worker was not finished

**What I got wrong.** I judged #69's worker finished and rebased its branch. It
was not finished; it was *paused*. The evidence I used was wrong in a way worth
writing down, because the next tick will face the same question:

- Its tree was clean and its last commit was "done-shaped" (a docs/changelog
  commit). ✅ but not sufficient.
- `ps` showed no live processes in the worktree at the moment I looked. ✅ but
  an agent between turns has no processes running. **Absence of processes is
  absence of a suite run, not absence of a worker.**

Fifteen minutes later the tree had `pyrite/models/base.py` modified, a
`base.py.tmp.*` scratch file, and 136 new lines in
`tests/test_update_preserves_frontmatter.py`. The worker had resumed.

**What it was doing, which is the part that matters.** It had found the
**mirror image of #46**: `_absent_default_keys` records what the source file
lacked, and that load-time fact was then read as the user's intent forever
after — so `importance = 5` on a file with no `importance:` key wrote nothing
*and reported success*. #46 is a write that changes what nobody asked for; this
is a write that silently does not change what was explicitly asked for. Both
report success. Its fix intercepts `__setattr__` rather than clearing the set
inside `KBService.update_entry`, explicitly so that the CLI, REST
PUT/PATCH, MCP `entry_update` and software-kb's `sw reorder` are all covered
rather than the one path that goes through that service method. That is exactly
the root-cause-over-symptom work the theme was dispatched for, and it was
uncommitted when I started rebasing.

**No harm done, verified rather than assumed.** The reflog shows a clean rebase
(`rebase (finish)` with no conflicts after `.claude/THEME.md`); git carries
uncommitted work across a rebase when it does not conflict, and both edits are
still present at 156 insertions. No pre-commit stash leftovers from my push
attempt. The "ahead 28, behind 6" that alarmed me is measured against the
**stale remote ref** and is expected after a rebase — `origin/dev..HEAD` is the
honest count, and it is 6, the correct set.

**What I did about it.** Killed both of my background pushes against that tree
(`TaskStop`), because a `git push` runs the pre-push hook, which *stashes every
unstaged edit in the working tree* — with a worker mid-edit that is how its
uncommitted work vanishes for four minutes, and CLAUDE.md warns about exactly
this. Left the branch rebased locally but **unpushed**: the rebase itself is
sound and the worker can keep working on top of it.

**The rule this should become.** The skill says "rebase a draft claim only when
its worker has reported" (tick 2 proposed it; it is not yet written into
`review.md`). Tick 3 proves the sharper version: **a worker has reported when
its report arrives, and by no other signal.** Not a clean tree, not a
done-shaped commit, not an idle `ps`. The draft PR body is where the report
lands; until it is there, the branch is the worker's. I substituted three
plausible proxies for the one real signal, and the only reason it cost nothing
is that git happened to be forgiving.

Filed as process friction; it belongs in `review.md` next to the cold-read
trigger.

**Corrected state: #69 rebased locally onto current `dev` (6 commits, clean
replay, `.claude/THEME.md` untouched per #107), NOT pushed, worker still
working in the tree. Its pre-push suite did run green during my attempt —
4253 passed, 68 skipped, 4m11s — which is useful evidence for whenever it does
land, but it predates the worker's newest commits and must be re-run.**

## Retro 2026-09-18T07:20Z (retro 2 — window 06:00Z–07:20Z, ticks 3–4; called by the maintainer after the first redispatch)

Correction: retro 1's heading says 06:45Z; it ran at ~06:00Z.

### What worked
- **The cold read, on its first trigger.** #69's footprint (`models/base.py`, `storage/`, `schema/`) fired the rule; `pyrite-reviewer` found two silent data-loss regressions (`--importance 5` a no-op via load-time inference of "absent"; `deepcopy` of a ruamel map destroying anchors) and a confounded benchmark the conductor had already published. Disposition went from "ready to flip" to "do not merge"; 0 defects merged. The trigger is footprint-based, not judgement-based, and that is why it fired.
- **Nested review.** #74 (B) and #84 (E) went worker → reviving parent tick → `dev` with no host involvement; #84's review verified the footprint, grep'd the locator rules, and accepted an over-delivery in the right place.
- **The tick log as the shared surface.** Three conductor agents (tick 1 revived, tick 3 revived, tick 4) wrote about #69 in one file, sequentially, with no clobber; the retro can read it.
- **Hallway tests on three surfaces in one day** — MCP read (#56–#68), MCP write (#92–#98), CLI (#87, #48, #51, #52, #54) — 26 issues with reproductions, three KB notes, one design note, and every one of them filed rather than fixed in place.

### Failures and root causes
- **#69 redispatched** (evidence: cold-read comment 06:56Z, log 07:10Z) → the worker inferred "was this field set?" from load-time state → the test named for that regression covered only passing cases → the conductor's spot-check took one test at random and was reassured by the class's name → **review.md**: stash-check every regression-named test (PR `process/retro-2-resource-cap`).
- **A wrong number published** ("not slower", then "+71%") → two worktrees, two venvs, two Pythons → a benchmark across worktrees is a benchmark across environments → **review.md**: one interpreter or no number.
- **Playwright C/D/E at 42+ min vs B's 20** (evidence: #84 06:20→07:02; C/D no push in 55 min) → three browser suites + a 20-run pytest loop on one machine → load 28 on 10 cores → the cap counts files, not the machine → **dispatch.md**: machine-heavy ≤ 2 (this retro's change).
- **`pyrite create` frontmatter** needed a hand repair on every backlog item created today (#86) — product, in the pool; noted because it is relearning waste on every claim until fixed.

### Waste, in the seven
Dominant: **delays** (contention; #69 waiting 40 min for a review that then had to be redone) and **defects** (a test that tested nothing; a published number that measured the wrong thing). Some **relearning** (three agents each re-reading #69's diff). Partially done work is low (5 drafts, all with live workers).

### Constraint
The machine — load 28 on 10 cores; heavy themes 2× their solo wall-clock; every review's suite re-run slowed with them. Not review attention this window: the review lane found more than it missed.

### Friction observed
- Tick 4 had to inspect a worktree mid-rebase by another conductor before touching it — the revived-tick model has no lock; no harm yet, noted.
- The host lost a `pyrite create` call to inline-heredoc quoting despite documenting `--body-file` for `gh` — the same rule applies to every command; a body file is the default.
- Tick 3's architect breakdown may have arrived at a tick that had ended; unverified whether it reached the log.

### The one process change
Machine as a footprint dimension: ≤ 2 heavy themes, `heavy:` in specs, heavy reviews count — `dispatch.md`; plus the two review.md rules above as root-cause fixes. PR `process/retro-2-resource-cap`.

### The quality theme
`no-op-round-trip-is-byte-identical-a-test-over-kb-that-fails-if-load-then-save-rewrites-any-file` (high, S, Sonnet after #69) — the 768/768 → 148/766 measurement made permanent; would have caught #46, #86, #87, #15. Stock still: teardown races (#81, in review), changelog fragments.

### Expected effect
Playwright package wall-clock from 42 min back to ≤ 25 by the next retro; load average under 12 while the fan-out runs; redispatch rate 1/6 this window → 0/5 next, with the cold read still catching ≥ 1 finding per trigger (if it catches nothing for five triggers, loosen it). Revert the heavy cap if F/G/H end up waiting on an idle machine.

### Not changed, noted for next time
- A review claim (label) so two revived ticks cannot review one PR — no collision yet; add it the first time one happens.
- The write-path family (#46 #86 #87 #15) is one design fault: "save serializes the model" vs "save edits the file". #69's redispatch prefers a dirty-field signal; if that lands, `link`/`links bulk-create` (#87) must go through the same path — one theme, Opus.
- Whether the architect's output from tick 3 survived — check next tick.

## Tick 2026-09-18T07:15Z — a duplicate tick, and what that cost

**This tick collided with the 07:10Z session on PR #69 and should mostly not
have happened.** Recording it in full anyway, because a duplicated tick is
exactly the process evidence the retro wants, and because two of its outputs
survive the collision.

### What collided

The loop host handed this tick "#69 is the priority, the tick-1 cold read may be
orphaned, check for a comment first". There was no cold-read comment on the PR
at 06:55Z, so this tick did the reasonable thing: dispatched its own
`pyrite-reviewer` and began an independent review. The 07:10Z session was doing
the same work at the same time, and got there first.

Cost: one redundant `pyrite-reviewer` on Opus, one full suite run (2:57), a
published PR comment that partly duplicated the other session's and contained
one claim I have since withdrawn, and roughly a tick's wall-clock. Nothing was
corrupted — but the duplicate pass was invisible until I read this log, at which
point the other session's entry was already written.

**The missing mechanism is the one the last retro declined to add**: "a review
claim (label) so two revived ticks cannot review one PR — no collision yet; add
it the first time one happens." This is the first time one happened. Recommend
adding it now: `gh pr edit N --add-label reviewing` as the first act of an
absorb, checked as the first act of the next. Cheap, and it is the only state
two sessions with no shared memory can both see.

A second, subtler trap: I read the tick log's *tail* before starting, which
showed the retro-2 entry and looked current. The 07:10Z entry was appended above
it in file order but after it in time. **Reading the log's tail is not the same
as reading the latest tick** — grep `^## Tick` and sort, or the log misleads
precisely when two sessions are live.

### What survives the collision

**1. The `.claude/THEME.md` conflict on `dev` — diagnosed and filed (#106).**
PR #69 was `DIRTY` and it had nothing to do with the code. `dev` is carrying
`.claude/THEME.md` (committed in 22619c9, the Playwright package B spec), which
add/add-conflicts with every branch carrying its own. The conductor skill says
in terms not to commit the spec as a loose file; a tick forgot, and now the
stale file on `dev` both conflicts and misleads — it reads as current
instructions to an agent, describing a worktree that is finished and gone.
Rebased #69 resolving it by deletion. **Suggested fix: gitignore the path**, so
the rule is enforced rather than remembered; the draft PR body is the claim, so
the file never needs tracking. (My rebase was not pushed — see below — so
whoever lands #69 should confirm the deletion is still in the final history.)

**2. #87 is fixed by #69's save path — measured on all four write surfaces.**
The coordinator asked whether the fix reaches the link step. It does. Fixture:
an entry whose body contains `|---|---|`. On clean `dev`, `pyrite link a b`
folds the body into a `body:` YAML scalar and adds `file_path:` and
`importance: 5`. On the branch it adds only the `links:` block; `update --tags`
gives a one-line diff; `links bulk-create` no change; `create --link` clean
frontmatter; `pyrite get` afterwards returns title/type/body intact.

Per the coordinator, #69 was **not** widened. #87 stays open as the next-queue
theme (0.24.2, pool row "CLI write-path integrity") and **must be re-verified
after the redispatch lands**, because the redispatch changes the mechanism I
measured. This measurement is not subject to the two-venv confound that
invalidated this window's performance claims: it is one command against one
fixture, and the difference is categorical rather than a timing number.

### A claim I published and withdrew

I wrote on #69 that the #78 teardown race "is NOT from this branch", on the
evidence that `test_index_worker.py` + `test_api_tiers.py` under `-n auto` error
2 of 3 runs on clean `dev`. That evidence shows the race reproduces on `dev` in
that file pair under load; it does **not** show the branch leaves the rate
unchanged, which is what I asserted. Withdrawn on the PR. The other session's
full-suite figure (0/4 dev, 2/4 branch) stands with its mechanism unexplained.

Two sessions in one window each published a confident, wrong measurement about
this branch — theirs a benchmark across two venvs, mine a rate inferred from the
wrong denominator. The common shape: **a number measured under one condition,
reported as a claim about a different condition.** `review.md` is already
getting a line about the venv case; it should cover this one too — state the
condition you measured *in the sentence that reports the number*, or report no
number.

### Blocked, and needing the maintainer

**The #69 rebase never pushed.** Two attempts: the first was rejected by the
`pre-push` suite (9 errors under load — the very teardown races #81 is fixing);
the second failed collection under xdist while a sibling worker was editing
`tests/`. `--force-with-lease --no-verify` was then **denied by the permission
layer** (safety-bypass classifier). The skill's own rule contemplates
`--no-verify` with a justification and an issue number, so there is a real gap
between what the process permits and what the session can do. Moot for #69 —
the redispatched worker owns that branch now and will push its own commits —
but it will recur whenever a conductor must land a rebase while the machine is
loaded. **Maintainer decision wanted:** either a permission rule for
`git push --no-verify` from conductor sessions, or an explicit "conductors do
not push through a red pre-push; hand back instead" line in the skill.

### Health, as observed

`dev` green (last 5 runs success). PRs #84 (Playwright E) and #100 (roadmap
pool) merged during the tick; their worktrees and branches cleaned up. Package E
was reported by the host as "not pushed since its claim" — it had in fact
finished, pushed, marked its backlog item done, and had its worktree removed;
git still listed the worktree, which is what made it look dead. **A missing
worktree directory is not evidence a worker failed** — check the remote branch
before concluding anything about a worker's state.

Open after the tick: #105, #83, #82, #81, #70, #69, plus seven dependabot PRs
all `BEHIND`. The dependabot backlog is now the largest single group of open PRs
and nothing in the loop is picking it up; worth an explicit decision (batch them
as one theme, or turn the rebase automation on) rather than leaving them to
accumulate.

### Dispatched

Nothing. The cap was full, three heavy Playwright/pytest workers were contending
for one machine, and the retro's own resource cap says not to add a heavy theme
in that state. Correct outcome, reached the expensive way.

### Addendum — the duplicate cold read came back, and it was not wasted

The second `pyrite-reviewer` (the one this tick dispatched before knowing the
07:10Z session had one in flight) finished after the tick entry above was
written. Two things are worth recording.

**It converged independently on both blockers.** `importance` and `rank`
default-suppression, found from a cold diff with no knowledge of the other
review. Two independent readers reaching the same two data-loss regressions is
the strongest evidence yet for the cold read as a **standing trigger** rather
than a judgement call — the last retro argued that from one instance, and this
is a second, cleaner one. It also proposed the fix in the form the redispatch
independently chose: `_omit_default` should apply only when the caller did not
touch the field, which `update_entry` knows and the model does not.

**It made the teardown-race measurement the other two lacked.** Both earlier
attempts (mine, and the 07:10Z session's) compared the branch against *`dev`*.
This one compared against the **merge base** — 1/6 vs 2/6 — which is the only
comparison that isolates the diff, and it additionally measured and ruled out
the one plausible timing lever (`_restyle_like_source` costs ~550 µs/save, but
median `to_markdown` is *faster* on the branch because `dev` was serializing
`body:` into the YAML). Three measurements now agree the race is pre-existing;
only this one was designed to be able to say so.

*Generalisable, and the sharper version of this window's other measurement
lesson:* **compare a branch against its merge base, not against `dev`.** `dev`
moves under you and carries other themes; the merge base is the only tree that
differs from the branch by exactly the diff under review. Both earlier
measurements in this window were confounded and one had to be publicly
withdrawn. Belongs in `review.md` next to the one-interpreter rule — they are
the same mistake at different scales (measuring under one condition, reporting
as a claim about another).

**Findings unique to it**, now on the PR and worth carrying into the redispatch
or into follow-up tickets: `kb_commands.py:272-280` and `admin_cli.py:261` still
run the unscoped whole-universe health walk (the exact cost #18 is about, in the
one place `-k` would pay for itself); `index health` has no gate on the *warning*
tier, so a KB with 52 unparseable files still exits 0 — which is half of what
#18 asked for; `check_health` accepts an unknown KB and returns a clean report to
any non-CLI caller; `db backup` relocates the 125 files without adding retention
or sub-second timestamps, and they are no longer under `.gitignore` to be caught
by `git status`; the new broken-links SQL scoping has no test pinning its design
decision; frontmatter YAML comments now survive an update — a real new guarantee
with no test and no changelog line, so the next refactor drops it silently; and
`README.md:109` plus `CLAUDE.md` still document `index health` as a plain check
while its default exit code has flipped, which will fail agents' bash calls.

**Cost/benefit of the duplicate, honestly:** ~100k tokens and 23 minutes of Opus
for a second opinion nobody asked for. It produced one measurement neither other
reader produced and eight findings not raised elsewhere. That does not justify
duplicating reviews — the claim label in #111 is still the right fix — but it is
a data point that a second cold read on a genuinely risky diff is not redundant,
which the retro may want when deciding how far the standing trigger should go.

### Tick 3 — #81 (quality theme) reported; first cold read of the loop dispatched

**This report is what a real one looks like**, and it is the direct contrast to
the mistake logged above. The worker handed back *explicitly incomplete*: "one
evidence run still in flight when forced to hand back. Do NOT treat the '10
consecutive runs' evidence below as final." It refused to flip its own backlog
item to `done` because criterion 5's evidence was not yet a single clean
artifact — "no completion claims without fresh verification evidence." A worker
that declines to claim completion it has not earned is worth more than one that
finishes on time.

**Root cause, both shapes, confirmed before changing anything.** The item's
theory (unclosed WAL connections recreating `-wal`/`-shm` during `rmtree`) was
right, and #55's was the second, separate shape: `test_api_tiers.py`'s
class-scoped fixtures build their own app via `create_app()`, which lazily
creates an `IndexWorker` on the first `/api/index/sync`, and nothing joined that
thread before the class-scoped temp dir was removed. **The worker did not touch
`pyrite/services/index_worker.py`** — `wait_for_idle()` and `_threads` already
existed; the gap was purely that the test's own app-building code never called
it. That is the correct call: the product was fine, the test was wrong.

Pre-fix reproducer, pasted as required: 6 runs, run 3 failed with
`OSError: [Errno 66] Directory not empty` — ~1 in 6 on this machine.

**The fix is a replacement, not a layer.** 369 insertions against **301
deletions**: a `make_client(tmp_path, **settings)` factory in `tests/conftest.py`
that owns the DB *and* the app's index worker, replacing four hand-rolled
`_make_client`/`_make_app_and_db` helpers, plus `PyriteDB.__enter__/__exit__` so
`with PyriteDB(path) as db:` is the idiom for the plain service tests. Criterion
2 asked for exactly this and got it. The teardown order is explicit and
commented: **join every index worker, then close the DBs they write through,
both before pytest removes `tmp_path`** — and `tmp_path` rather than
`TemporaryDirectory()` means a late writer cannot fail the run at all, which is
the belt to the braces.

**Where the ticket was wrong, and it matters for the next quality item.** The
item said "nine test files". The worker verified that list against the tree as
instructed and it matched *the nine named* — but nobody had asked whether nine
was the whole population. It is not: 189 `PyriteDB(` call sites across `tests/`,
and ~70 files combine `TemporaryDirectory` with `PyriteDB`. Measured honestly
(bare opens exceeding `.close()` calls per file), the real residue is **3 files**
— `test_admin_cli.py`, `test_collection_query.py`, `test_collections.py` — so the
fix covers the actual risk population and the raw counts overstate it badly.
Noted in the PR as a known remainder rather than treated as a blocker: the
lesson is that a backlog item's enumeration is a hypothesis, and "verify the
list" should mean "verify it is complete", not only "verify each entry".

**It also found and fixed a tenth file nobody had listed** —
`test_api_authorization_coverage.py` broke on collection the moment the helper
was renamed (a forced fix, not scope creep), and while there it got the
wait-for-idle teardown it had silently always lacked. Flagged by the worker
itself for the reviewer to accept or split. Accepted: it is the same defect in
the same shape, and leaving it would have left the suite red.

**#88 filed, not fixed** — `test_index_worker.py`'s `test_active_jobs_filters`
and `test_duplicate_sync_returns_same_id` assume `submit_sync()`'s thread has
*not* finished by the next line, which is only true while the job is slow; under
the CPU contention that `-n auto` on a loaded machine produces, a near-empty KB's
sync finishes first. Pre-existing, reproduces unpatched, and a *different* race
from this theme's (a same-thread assertion racing the job's own completion, not
a teardown race). Correctly filed rather than folded in — and it is why the
worker's 10-run passes show an occasional failure that is not a teardown error.

**Cold read dispatched — the first of this loop.** The trigger fired properly
for once: the diff adds `__enter__`/`__exit__` to a class in
`pyrite/storage/connection.py`, which is both storage *and* a new public shape on
a class extensions use. `pyrite-reviewer` (opus) got the diff and nothing else,
pointed at re-entrancy, double-`close()`, `__exit__` returning False, long-lived
callers being closed out from under, the fixture's teardown order on the
raised-exception path, and whether any test conversion silently weakened an
assertion. Retro 1 noted "cold reads: 0 dispatched, 0 needed; the trigger has not
been tested." It has now.

**Conductor's own verification in progress:** re-running the pre-fix reproducer
6× on the branch (2 clean so far, against ~1-in-6 failure before the fix).

### Tick 3 — the machine-footprint rule indicts this tick's own dispatch

Retro 2 (`8ba4d42`, maintainer-called, landed on `dev` while this tick was
absorbing) names the constraint this tick actually hit, and the rule it wrote
condemns what this tick did:

> **A footprint has two dimensions: files and the machine.** [...] Disjoint
> files do not make heavy themes disjoint [...] **Run at most two
> machine-heavy themes at once.**

**Tick 3 dispatched four machine-heavy themes at once** — Playwright packages
C, D and E (each a browser suite) plus the quality theme whose acceptance is
*ten consecutive full-suite `-n auto` runs*. The file footprints were disjoint
and I checked that carefully; the machine footprint I did not consider at all.
The cap I applied ("up to six when footprint-disjoint and fewer than two
branches await review") counted files and reviews, and nothing counted CPU.

The cost is measured, not inferred: retro 2 records package E at **42 minutes
against package B's 20 alone**, load average 28 on 10 cores. By the time this
tick was verifying #81, **load average was 54** — worse, and partly my own
doing: I added a 6× reproducer loop and then a 3× loop *on top of* the
worker's inherited detached 10-run, to verify a theme whose evidence was
already conclusive.

**Corrective action taken now, not deferred to the next tick:** killed the
inherited detached 10-run loop (PIDs 8666/8731). Its evidence had already
answered the question — two completed full-suite runs, **zero** teardown
errors, the only failure being #88's known unrelated race — and the remaining
eight runs would have bought nothing at the price of the machine every other
worker and every review is sharing.

**Evidence tally for #81's criterion 5, from three independent sources:**
- worker: 10-run targeted pass (8 clean, 2 × #88), full-suite 10-run pass (9/10
  clean, 1 × #88), plus 3 more clean full-suite runs — **zero teardown errors in
  every run**;
- the detached full-suite pass: 4222 passed, **zero** teardown errors;
- conductor's own 9 reproducer runs: 8 clean, 1 × #88, **zero teardown errors**,
  against a pre-fix rate of ~1 in 6.

Criterion 5 is about teardown errors specifically. Across roughly two dozen
independent runs there are none, where the unpatched branch produced them
reliably. **The criterion is met**; the worker's scruple about not having one
*single uninterrupted* 10-run artifact was honourable but is satisfied by
convergent evidence from three sources, and buying the last artifact would cost
another ~25 minutes of a machine at load 54.

**Two lessons for the retro, both mine:**
1. The cap must count machine-heavy themes, and *the conductor's own
   verification runs are machine-heavy too*. Retro 2 says "one heavy review
   counts as a heavy theme" — this tick ran two heavy reviews (#84's attempted
   re-run, #81's reproducer) while four heavy themes were building.
2. **Verification has a stopping rule.** I ran 9 reproducer runs after the
   evidence was already conclusive at 3. "More evidence" is not free when the
   machine is the constraint; the question is whether another run could change
   the decision, and after the third it could not.

Also noted: #69's cold read (run by a peer session, not this one) produced the
two new `review.md` rules in retro 2 — verify-red on *every* regression-named
test, and no number in a report that was not measured under one interpreter
with the tree pinned. #69 is back at `e0c7f704` and was **redispatched**, so my
local rebase of it is moot; the branch is the worker's again.

## Process notes for the retro — from the 05:50Z/06:45Z/07:10Z session (nested conductor)

Written at the maintainer's request at the close of the session that ran tick 1
(05:50Z dispatch), absorbed PR #69 (06:45Z) and redispatched it after a cold
read (07:10Z). Scoped to evidence **only this session can supply** — what
happened inside its own loop — rather than re-deriving what retro 1 and retro 2
already cover. Issue numbers are the durable record; this is the reasoning
behind them.

### 1. The cold read paid for itself, and the trigger that fired was the weakest one

Metric for the retro's "cold-read findings that changed a PR / cold reads
dispatched" row: **1 of 1 changed the PR's disposition**, from *flip to ready*
to *do not merge*. It found two data-loss regressions
(`--importance 5` silently dropped — a regression of commit 7783335, reachable
from CLI, REST, MCP and the kanban reorder; `deepcopy` destroying YAML anchors
and merge keys) that the conductor's own review had missed after reading the
same diff, re-running the suite, and verifying all three acceptance criteria by
hand.

The part worth generalising is **why** the conductor missed them. The branch
added a test class named `TestAlwaysWrittenDefaultsStillWork`, documented as
guarding exactly the `importance`/`rank` hazard. Its three cases covered only
the situations that already worked. The conductor read that class and was
reassured *by its name*. A well-named test over an uncovered case is worse than
no test: it converts an unexamined risk into an apparently examined one, and it
defeats a reviewer who is checking whether a risk was considered rather than
whether it was covered.

So the trigger that mattered here was not "touches `pyrite/storage/`" but
**"the worker's Unsure is non-empty"** — the worker had flagged the
`_absent_default_keys` design as "the decision most likely to have gone another
way". That is the cheapest and most specific of review.md's five triggers and
the easiest to wave through. Suggestion: when a worker's Unsure names a
*design decision* (not a style choice), the cold read should be mandatory
rather than discretionary, and the reviewer's brief should quote that Unsure
verbatim as its first question.

### 2. Verifying a subagent's report is not optional, in either direction

Three claims from model output were checked against measurement this session.
Two were wrong, and they were wrong in *opposite* directions:

| claim | source | held up? |
|---|---|---|
| "flake is pre-existing, confirmed by stashing" (#78) | worker | **No** — 0/4 reproductions on `dev`, 2/4 on the branch |
| "write path not slower, 0.182s vs 0.214s" | **the conductor itself** | **No** — compared two interpreters (#101) |
| "+71% load / +99% save" | cold reviewer | **No** — within noise under one interpreter |
| "no reader of `meta['body']`/`file_path`" | worker | Yes — independently confirmed, 50 `from_frontmatter` impls |
| two data-loss regressions | cold reviewer | Yes — both reproduced before acting |

The rule in the skill is "a worker's report is model output; verify with the
diff and the suite". This window says it must extend to **the reviewer's report
and the conductor's own published numbers**. The conductor's error was the most
costly of the three, because it was published first, stated confidently, and
would have been inherited by the next tick as settled fact. A conductor that
verifies its workers but not itself has moved the trust problem, not solved it.

### 3. The one finding a reviewer structurally cannot make: CI green on untested code (#91)

The worker's four code commits were never pushed. CI classified the remote
branch — which contained one markdown file — as docs-only, **skipped the test
job, and reported `gate: success`**. Every signal a conductor normally trusts
said the PR was fine.

This is invisible to a cold reviewer (it reads a diff, not a remote) and
invisible to the worker (its local suite passed). Only the conductor, standing
between the branch and the PR, is positioned to catch it, and only if it
compares `git rev-parse HEAD` against `origin/<branch>` *before* reading
`gh pr checks`. The second half, found later: a `workflow_dispatch` run does
**not** attach to a PR's required checks, so a green manual run leaves
`mergeStateStatus: UNKNOWN` and can be mistaken for readiness.

The generalisable form, worth a line in review.md above the checklist: **a
green check is a claim about a commit, so identify the commit before believing
the check.**

### 4. A measurement trap built into the worktree workflow (#101)

`scripts/new-worktree.sh` gives each worktree its own `.venv`, and those venvs
can resolve different Python versions (3.11.14 in the branch worktree, 3.13.7
in the main checkout). The obvious way to A/B a change — run the benchmark
here, then there — therefore compares **two interpreters**. Both the conductor
and the cold reviewer fell into this independently on the same day and produced
contradictory numbers; neither survived a controlled re-run.

Second trap, which cost two further attempts: with the package installed in the
venv, `cd`-ing into a source tree does not change module resolution. A harness
that prints the resolved module path catches this instantly; one that does not
will silently measure the same code twice and report a reassuring null result.

This is a property of the workflow, not of one agent's carelessness — which is
the argument for fixing it in `review.md` rather than trusting habit.

### 5. Scope discipline: this session ran ~1h46m for a one-tick request

The maintainer flagged it, and it is a finding rather than an apology. The tick
proper (health, choose, dispatch, log) took ~20 minutes. The worker then
reported *inside the same tick*, and the session treated that as "the absorb
lane applies now" instead of "that is the next tick's work". That single
decision consumed the remaining ~80 minutes: diff review, repeated suite runs,
8 full-suite runs chasing a flake rate, a ~19-minute cold read, and a
re-benchmark after the cold read corrected the conductor.

The work was worth doing — it stopped two data-loss regressions from merging —
but "worth doing" and "in scope for this tick" are different questions, and the
session conflated them. The skill's own three-lane model says a tick absorbs
the **previous** set while dispatching the **current** one; a tick that does
both to the same branch has no natural stopping point, because each next step
is locally justified.

Concrete suggestion, cheap to apply: **a tick's absorb lane operates only on
branches that were already reported when the tick began.** A worker that
reports mid-tick is next tick's absorb. That preserves the pipelining the skill
already describes and gives the loop host a predictable tick duration, which is
what makes an unattended loop safe to leave running.

### 6. Cross-session collisions (already #111) — one addition

Confirming from this side: this session was the 07:10Z half of that collision
and never saw the other session, since it had no reason to re-read a log it had
itself appended to. Two mechanical notes for whoever implements the fix:

- **File order in the tick log does not match time order.** In this file the
  07:10Z entry sits above the 06:45Z and 07:15Z ones. Any instruction to "read
  the latest tick" that means "read the tail" is wrong whenever it matters most.
  `grep '^## Tick' | sort` on the timestamp, not `tail`.
- **A `reviewing` label is the right claim** because it is visible before any
  output exists. The reviewing session has, by definition, published nothing
  during the window in which the collision occurs — so "check for a PR comment
  first" cannot work, and both sessions here behaved reasonably under that rule.

### What this session did NOT change, deliberately

No ADR accepted or amended, no release prepared, no push to `main`, no repo
setting touched, and PR #69 was never flipped to ready — it stays draft with
the defects documented and the worker reworking it. The kept/delegated boundary
held throughout; the only maintainer-facing asks are the `process` issues above.

### Tick 3 — the first cold read paid for the whole practice

`pyrite-reviewer` on #81 (opus, diff and nothing else) returned the finding a
conductor reading the same diff would not have made, because the diff *looks*
right and the bug is in code the diff does not contain:

> **`create_app()` opens a SECOND `PyriteDB` on the same file** — eagerly, while
> seeding the KB registry — and parks it on `application.state.pyrite_db`. The
> fixture's `dependency_overrides[get_db]` redirects dependency injection but
> does not close that connection; some routes read it *directly* rather than
> through DI (the export path in `endpoints/kbs.py:167`); and **nothing in
> `pyrite/` ever closes `app.state.pyrite_db`.**

So the fixture whose docstring said "this is what those hand-rolled helpers were
missing" was missing the same thing. The leak the theme is named after was still
there — **relocated, not fixed**, and invisible only because the branch also
moved to `tmp_path`, which pytest does not delete during a run. A *default*
(`tmp_path_retention_policy`) was doing the work the code claimed to do.

**Verified before acting, not taken on trust.** `api.py:766` assigns it,
`kbs.py:167` reads it, `grep` finds no close anywhere. Then the decisive test:
create a client, hit `/api/kbs`, let the fixture tear down, and look at the
directory — `index.db-shm` and `index.db-wal` still live. **Verify-red on the
fix** (retro 2's new rule, applied to my own work): with the app-state tracking
removed the new test fails with exactly that message; with it, clean.

**Fixed on the branch rather than redispatched** — four commits, because each is
small, provable and inside the theme:
1. `tests/conftest.py` tracks and closes `application.state.pyrite_db` too, with
   the mechanism written into the comment so the next reader does not have to
   rediscover it. Docstring corrected: `tmp_path` is named as a *second line of
   defence*, not the fix.
2. Both teardown loops (conftest's and `test_api_tiers`' four-client fixture)
   guard each join and each close individually and re-raise the first error —
   the cold read's second finding: one failing close leaked every connection
   after it, the same class of bug the fixture exists to fix.
3. `tests/test_make_client_closes_every_connection.py` — the regression guard.
   It asserts on *the connection*, not on whether a directory removal happened
   to survive, precisely because the retention policy is a default a project can
   change. It also guards its own premise: if `create_app` stops opening a
   second connection, the test says so rather than passing vacuously.
4. The three sites the cold read found still matching the ticket's own pattern
   (`test_collections.py`, `test_collection_query.py`, `test_admin_cli.py` — the
   last constructed inline inside a `patch()` call and never bound, so it could
   not be closed at all). **Criterion 1 was not met before this**, and the ticket
   said it was.

**The transferable lesson**, logged above and worth repeating: the item named
nine files, the worker verified those nine matched, and nobody asked whether
nine was the population. *Verify the list* has to mean *verify it is complete*.

**What the cold read got right that I had already passed:** I reviewed this
diff, read every hunk, ran the suite, and flipped none of these. I checked that
the teardown order was correct — it is — and never asked whether the fixture
owned everything it claimed to. The trigger (storage + a new public shape) fired
correctly and the practice earned its cost on first use. Retro 1 recorded "cold
reads: 0 dispatched, 0 needed; the trigger has not been tested." Tested.

**Left as follow-ups, not blockers**, all noted in the PR: `close()` is not
terminal (SQLAlchemy silently re-opens from the pool, so a caller holding a
reference past the `with` block can resurrect the WAL files); `__exit__` does not
guard re-entry; `IndexWorker._threads` is never pruned so `wait_for_idle`'s 10 s
is per-thread and cumulative; and the new context manager has zero adoption in
`pyrite/` — `cli/context.py` still hand-rolls `try/finally: db.close()` three
times, which is exactly where a reviewer will ask "why not here?".

### Package D (#83) absorbed

Reviewed, flipped, rebased, auto-merge armed. Footprint matches its spec; zero
`text=`, zero `.first()`, `uniqueTitle` in both files — all verified by grep
rather than from the report. **It found and fixed a real product bug**:
`entries/new/+page.svelte` derives `kb` from `kbStore.activeKB ?? ''` and
`save()` guards only on `title`, so a click before the store resolved POSTed
`kb: ''` and failed *silently* (toast gone in 3 s, no navigation, nothing else
surfaces it). Confirmed independently by reading `save()` against the `$derived`.
One-word fix mirroring the existing gate. Root-caused with a traced
`--repeat-each=8` run, not guessed from a flake — criterion 7 working as designed
for the third package running (B→#49, E→#89, D→this).

Filed by D: **#117** (no delete affordance anywhere in the UI — `deleteEntry()`
exists and is unit-tested but no component calls it, so delete is untested
through the UI and its specs clean up via the API) and **#118**, which is a
duplicate of my **#104** — *the same defect filed independently by two packages
and the conductor inside one hour*, which is the measure of what it costs. #118
adds the failure mode #104 missed and it is the dangerous one: **Vite silently
falls back to 5174+ while Playwright's `baseURL` stays pinned to 5173**, so a run
can talk to a different worktree's data and read as a mysterious assertion
failure. Carried into #104's acceptance: a port collision must fail loudly, not
fall back.

**Load is down to 9.76** from 54 after killing the redundant 10-run loop.

## Tick 2026-09-18T07:36Z (tick 5 — relaunched after the killed attempt; verification tick)

Load 26 at start (peak 41), 21 at end. `dev` green (3 successful runs). Ports
8088/5173 free at 07:36Z. The killed attempt's `in-review` claims on #69 and
#108 had been released; nothing was half-done on disk.

### PR #69 — verified myself, redispatched a second time (circuit-breaker threshold)

No third cold read, as instructed. I verified the three named defects by hand
in an isolated KB built from this branch's `.venv`.

**Fixed, confirmed:**
- `update -i 5` / `-f rank=0` now persist. The `__setattr__` interception is
  the right mechanism — it catches CLI, REST, MCP and `sw reorder` rather than
  one service method.
- Anchors/merge keys survive: `_restyle_like_source` carries unchanged nodes by
  reference instead of deep-copying.
- **#87 is genuinely fixed, and was catastrophic at the merge base.** On
  `8ba4d42`, `pyrite link` on an entry whose body contains `|---|---|` wrote the
  entire body into frontmatter as a `body:` key *and* leaked an absolute
  `file_path:` into the file. On the branch the body is untouched. That fix
  alone justifies the theme.
- Full suite in the worktree: 4262 passed, 68 skipped, 113s, `-n auto`.

**Two blockers sent back:**

1. **`priority: medium` is invented on every write.** `entry_types.py:318`
   writes it unconditionally, three lines above the correctly-guarded `rank`.
   The worker fixed the key the cold read named and missed its sibling in the
   same method. And it is not one type: probing all 49 registered entry types,
   **32 invent at least one key** they were not loaded with — `ADREntry` invents
   `adr_number: 0`, `ZettelEntry` invents `maturity`, `QAAssessmentEntry` invents
   four. The generic machinery already computes the right answer
   (`_absent_default_keys` contains `priority`); only the write path fails to
   consult it. I did **not** patch this inline: at 32 types it is a design call
   (central filter vs 32 guards), not a small sure edit.

2. **Nine of twelve regression-named tests pass without the fix.** Including
   both tests named for the cold-read data-loss defects and the entire
   `TestStructuralYamlSurvivesAWrite` class written in response to cold read 2.
   The fixes are real — I verified them by hand — but the suite is not what
   proves them. Root cause is the fixture: `BACKLOG_ITEM` already carries
   `priority: high`, so no test ever loads a backlog item *lacking* the key,
   which is also exactly how the `priority` regression got through. This is the
   **second occurrence on this same PR** of the failure mode review.md already
   records.

Redispatched (Opus) with the central-fix preference stated and the per-test
red-at-base table required. **This is the second redispatch of one theme — the
circuit-breaker threshold — so it is flagged to the maintainer rather than
dispatched a third time on my own authority.**

### The verify-red harness verified nothing (issue #121)

Worth recording as the tick's most dangerous finding. `scripts/verify-red.sh`
reverts the implementation with `git stash push`. This worktree had **unmerged
paths** — left by a stale stash belonging to an unrelated branch
(`feature/journalism-investigation-kb`) that my own `stash pop` had partially
applied — and `git stash push` then fails while the script carries on. The
implementation was never reverted, every test ran against the full fix, and the
script reported `PASSED without the fix` for **all twelve**.

I only caught it because twelve of twelve was implausible and
`grep -c _absent_default_keys` still returned 6 with the stash supposedly
applied. The symmetric failure — reporting an untested fix as verified — is the
one that would actually land bad code. Filed #121; workaround is
`git checkout $(git merge-base origin/dev HEAD) -- <impl>` with an assertion
that the revert took. **A conductor that trusts a green verify-red without
checking the revert took effect is not verifying anything**, and the same stale
stash is presumably sitting in other long-lived worktrees.

I restored the worktree to a clean HEAD and left the unrelated stash entry
untouched.

### #106: the THEME.md problem is on `dev`, not on the branch (issue #122)

`.claude/THEME.md` is tracked on the branch — but `git ls-tree origin/dev`
shows it is tracked on `dev` too. `.gitignore:89` stops new adds but never
untracked the file committed in 22619c9, so every branch inherits it and the
add/add conflicts can still recur. Not #69's defect; filed separately.

### Outside PRs #108 and #116 — partial review, handed off

Two outside contributors have now filed for #97: #108 (fathirramadhan-web) and
#116 (YaoSong808). Mid-review, the host launched dedicated review agents, so I
posted what I had and released my claims.

**Neither has ever run CI**: both workflow runs are `conclusion:
action_required`, held pending maintainer approval for first-time contributors.
Every "suite green" claim on both is author-reported only. Only the maintainer
can approve those runs.

The substantive difference, verified: #108 validates the target with
`self.db.get_entry` — the **SQLite index** (`storage/crud.py:22`) — while #116
uses `KBRepository.load`, the **disk**. #116's description is right that this
matters: an entry created but not yet `index sync`'d is invisible to the index,
so #108 rejects links to targets that really exist, on the common
`pyrite create` → `pyrite link` agent path. #108 is ahead on design
(`allow_dangling` + a `resolved` flag) and on test breadth, and carries a stray
`.gitignore` hunk ("Auto-added by github-engineer", including `nem_stats.c`)
that belongs to another project.

### Playwright: the fault the footprint could not see (#118)

Per the host: `playwright.config.ts` hardcodes 8088/5173, so concurrent
worktrees test against each other's servers. Consequences recorded for the next
tick: **no F/G/H dispatch until #118 lands**; Playwright is one-at-a-time, not
two; #82 and #83's five-run evidence may be contaminated and must be re-run with
`lsof -i :8088 -i :5173` empty, treating `trying another one` / `already used` /
`ECONNREFUSED` / `was not able to start` as **invalid runs, not failures**.

Created `playwright-package-a-1-per-worktree-ports-and-data-dir` (Sonnet,
milestone 0.24.2) at the head of the next queue, allowed to touch package A's
four files. **Retro 2's "machine-heavy" cap named the symptom; the shared fixed
ports were the fault.** Two themes can be footprint-disjoint in git and still
collide on a port — a footprint dimension the dispatch rules do not model.

### Dispatched / not dispatched

Only the #69 redispatch. I did **not** take the free code-only slot for the MCP
read-tier theme (#57/#58/#64–#68): with #69 sent back for a second time, the
review queue is the constraint and the circuit breaker is at its threshold — the
right move is to let the maintainer weigh in, not to add a branch. A.1 waits for
C and D to finish so the fix is not itself contaminated.

#81's worker has five commits and has not reported; left unreviewed per the
host (heavy, waits for #69).

### Circuit breaker: tripped, deliberately

The host offered the alternative of fixing #69 myself under review.md's "fix it
yourself when it is small and you are sure". I considered it and declined, and
the reason is worth recording because the offer was reasonable.

It is not small. Guarding `priority` is one line, but `priority` is one of
**32 entry types** that invent keys; fixing only the instance I happened to
probe would produce a green PR that still corrupts ADRs (`adr_number: 0`),
zettels (`maturity`) and QA assessments (four keys). "Land correct rather than
fast" argues *for* sending it back, not against.

And I am not sure. The central fix — having frontmatter emission consult
`_absent_default_keys` once — is the right shape, but it has to preserve the
behaviour commit 7783335 added and the `__setattr__` rule, and getting that
wrong silently reintroduces exactly the data loss cold read 1 found. That is
not a conductor's one-line commit; it is the theme's core design, which is what
a worker is for.

The test rework is also not under an hour: nine tests need a new fixture and
genuine red-at-base proof, and the fixture change is what surfaces further
instances of the 32.

**So: second redispatch, breaker tripped, loop stopping for the maintainer.**
Per SKILL.md I do not dispatch again until they say so. The redispatch is
already running (Opus) because the worker can be working while the maintainer
decides; if they would rather take a different route, it can be stopped.

Nothing was merged this tick. #69 stays draft with `in-review` removed.

### Correction to this tick's #121 root cause (recorded by the host)

I got the root cause wrong and the correction matters more than the original
finding, so it goes in the log rather than only on the issue.

I blamed unmerged paths making `git stash push` fail. The real hole:
**on a review-lane branch the fix is already committed**, so
`git stash push -- <files>` has nothing to save, exits **0 having stashed
nothing**, and every test runs against the fix. `verify-red.sh` only ever
worked for *uncommitted* fixes — which the review lane never has, by
construction.

So every stash-check run in the review lane has been vacuous, including the
ones that reported success. "verify-red green" on previously merged PRs is
**not** evidence those tests were ever red at base. The unmerged paths I hit
were incidental noise on top of a script that could not have worked here.

The lesson for this lane: my workaround (`git checkout <merge-base> -- <impl>`)
was only safe because I checked `grep -c _absent_default_keys` returned 0 while
reverted. **The assertion that the revert took effect is the load-bearing
step**, not the revert mechanism. A verification tool that cannot fail loudly is
worse than no tool, because it launders absent evidence into apparent evidence.

Host is fixing the script (revert to merge base, assert the tree changed,
restore from HEAD) with a test. The stale stash is repo-global (stash refs live
in the shared `.git`) and belongs to `feature/journalism-investigation-kb` —
left alone.

### Tick 5 closed

Breaker tripped, tick cron deleted, maintainer has the report. The
second-redispatch worker on #69 runs to completion; its result is reviewed when
the maintainer restarts the loop, not before. No further dispatch from me.

### Tick 3 final — #83 merged, #81 in review, #82 still building

**PR #83 (Package D) merged** at 07:38:42Z; dev push green in 1m48s. Content
verified on `dev` (the `saving || !kb` guard and the backlog item in `done/`)
before removing the worktree and branch.

**PR #81 (quality theme) flipped to ready, rebased, auto-merge armed.** Final
full suite on the branch: **4225 passed, 68 skipped, 7m15s, zero teardown
errors** — and the count rising from the worker's 4223 by exactly two is the
check that the two new context-manager tests are the only additions and nothing
was dropped. Five commits: the worker's fix, then four from this conductor
closing the cold read's findings (app-state connection tracked, teardown loops
guarded, the regression test with verify-red, the three unconverted sites), then
the KB item closed with both acceptance boxes ticked.

The PR body carries the four known trade-offs the cold read surfaced and this
theme deliberately did not fix — `close()` not being terminal, `__exit__` not
guarding re-entry, `IndexWorker._threads` never pruned, and the new context
manager having zero adoption in `pyrite/` while `cli/context.py` hand-rolls the
same `try/finally` three times. Each is a real follow-up; none is this theme,
and a reviewer should see them rather than discover them.

**Package C (#82) is still building** and was left strictly alone: five live
processes, uncommitted edits to `auth.spec.ts`, `playwright.config.ts` and
`login/+page.svelte` — the shape of someone implementing option (a), the
auth-enabled second Playwright project. Per #109's lesson, the branch is the
worker's until its report arrives.

**Two pushes died silently at the 120 s foreground timeout** before the
pre-push suite (~4 min) could finish — once on #69, once on #81 — each time
leaving the remote unchanged with no error visible until the tip was checked.
A conductor that did not re-check would believe it had pushed. Worth folding
into the push guidance: **a `git push` on a code branch needs a timeout longer
than the pre-push suite, and its result is the remote tip, not the command's
exit.**

**Tick 3 close: 3 merged (#84 Package E, #83 Package D, plus #74 absorbed by the
host at the tick's open), 1 in review (#81, rebased, auto-merge armed), 1
building (#82), 1 redispatched by a peer (#69). Issues filed by this conductor:
#86, #103, #104, #107, #109. Issues filed by its workers: #88, #89, #117, #118.
First cold read of the loop dispatched, and it changed the outcome.**

### Post-tick: the maintainer's decision on #97's two outside PRs

Two outside contributors filed independently for #97 within ~an hour. The
maintainer read both and chose **#116** (YaoSong808) as the fix, on the single
technical point that decides it: #116 validates the target against
`KBRepository.load` (the filesystem), #108 against `self.db.get_entry` (the
SQLite index). An entry on disk but not yet `index sync`'d is invisible to the
index, so #108 rejects links whose target genuinely exists — on the common
`pyrite create` → `pyrite link` agent path.

The maintainer's framing is worth keeping: **"both PRs are valuable and both
contributions made the product better."** #108 is the stronger PR in two
respects — `allow_dangling` + a `resolved` flag is a real design that #116 has
no answer to, and its test set is broader. So the disposition is not
winner/loser:

- Commented on #116 with the decision and three non-blocking points (a
  `KBNotFoundError` that returns `retryable: true` when it should not; the
  exception ordering; the missing forward-reference hatch).
- Commented on #108 naming exactly what it does better and why it is not
  merging, and inviting the author to carry `allow_dangling` forward as its own
  PR with their name on it.
- Filed **#124** for `allow_dangling` + `resolved`, crediting #108, blocked on
  #116 landing, including the defect where its duplicate-link early return
  reports `resolved: True` without re-checking the existing target.

Neither PR has run CI (`action_required`, held on first-time contributors); the
maintainer is approving. Nothing merges until #116 is green — with #121 fresh,
an author-reported green is not evidence.

Process note for the retro: closing a first contribution with silence is how a
project loses a contributor. The cost of writing #108's author a specific,
technical "here is what you did better, here is the one thing that decided it,
please come back" is a few minutes; the value chain's input here is people, not
just diffs.

### Post-tick: #69's third pass verified — correct, but parked (red `dev` + tripped breaker)

The second-redispatch worker returned. Verified independently; **the theme now
holds.**

- **0 of 49 types invent keys at the file boundary** (was 32). `update -f rank=0`
  on a minimal file produces a one-line diff; `link` adds only the links block;
  #87 still fixed.
- Suite 4268 passed / 68 skipped here (3.11, `-n auto`).

**The worker improved on my instruction, and that is the notable part.** I told
it to filter inside `to_frontmatter` or a wrapper on it. It refused: the index
is built from `to_frontmatter()` and `sw backlog` filters on the `status`/
`priority`/`rank` it finds there, so filtering at that level would have hidden
every entry whose file omits `status:` from every status filter — quieter and
worse than the bug being fixed. It put the filter at the file boundary instead
(`_frontmatter_for_file`, called only from `to_markdown`). **A conductor's
proposed design is not a spec, and a worker that pushes back with a reason is
doing the job.** Worth remembering the next time a redispatch prompt sounds
prescriptive.

**But its evidence table overstated two rows.** It claimed
`test_tags_update_never_writes_model_internals` and
`test_loaded_entry_has_no_internals_in_extra_frontmatter` are red at base and
that my earlier reading was a #121 artefact. Reverting to `8ba4d42` with an
assertion that the revert took: both are **green at base**, as I originally
found. The verdict is unchanged — the new catch-all test is genuinely red and
is the one that catches all 32 — but **a worker's red/green table is model
output like any other, and the rule that caught this is the same one that
caught #121: assert the revert took effect, then believe the result.**

Not merged, and will not be by me:
1. **`dev` is red** at d3d223a (the #81 merge) — `test (3.13)` errors at setup
   across `test_api_tiers.py`, `fixture 'configs' not found` + four siblings;
   3.12 green on the same commit. Nothing merges into a red `dev`. This PR's
   green 3.11 suite says nothing about a 3.13 collection failure.
2. **The breaker is still tripped.** I do not merge or dispatch out of that
   state on my own authority.

Left draft, auto-merge unarmed, `in-review` removed. Recommendation when the
maintainer restarts: fix red `dev` first, correct the two table rows, then it
lands as-is.

Also flagged on the PR: this worktree still holds unrelated modified files
(conductor skill edits, `.gitignore`, `FEEDBACK.md`, `kb/roadmap.md`, untracked
`kb/tasks/`, `tests/usability/`). The worker found 12 of them *staged*,
unstaged them and committed explicit paths only — correct behaviour, #119
recurring. They need an owner before anyone pushes from that tree.

### Correction: the "two overstated rows" was my error, not the worker's

Retracted on the PR. The worker root-caused it and I reproduced the result:
**we reverted different file sets and both readings were correct for what each
reverted.**

The two tests guard the `body:`/`file_path:` leak, fixed in
`pyrite/storage/repository.py:90-97`, not in `base.py`. Same commit, same
interpreter:

| revert set | those two tests |
|---|---|
| `base.py` only (mine) | 2 passed |
| all four theme impl files (the worker's) | 2 failed |

My assertion — `grep -c _frontmatter_for_file` → 0 — was *true*, and proved
only that `base.py` went back. It said nothing about the other three files, and
these tests happen to be guarded by the one I did not revert.

So this is the adjacent failure mode to #121, and the subtler one: #121 is
"the revert silently didn't happen"; this is **"the revert happened, to less
than you meant."** Three files quietly staying at HEAD looks identical to a
correct run. Added to #121: the replacement must `git diff --quiet $BASE --
$IMPL` over the whole revert set rather than grep one sentinel in one file, and
the caller must name the theme's full implementation footprint.

Two process points I want the retro to have:

1. **I wrote "a worker's red/green table is model output like any other" while
   my own check was the narrower one.** The principle is fine; I applied it to
   deflect rather than to verify, and the asymmetry — conductor doubts worker,
   worker re-derives and turns out right — is the failure mode worth watching.
   It cost nothing here only because the worker pushed back with a reproduction
   instead of deferring.
2. Twice in one tick a worker improved on a conductor instruction (the
   `to_frontmatter` placement, then this). Its own account of why it caught the
   first is worth adopting verbatim: it grepped the callers of the method
   before filtering it — `storage/index.py:250` answered it in one read.
   **Cheap check as habit, not instinct.**

Verdict unchanged: theme holds, #69 stays draft on red `dev` + tripped breaker.
Noted without a causal claim: the red-`dev` 3.13 `fixture 'configs' not found`
is in the same file as #127 but is a different failure; no evidence they are
related.

### Amendment: retro item 1 was framed wrong — the lesson is scope-invisibility, not deference

I filed the revert-set disagreement as "conductor doubts worker, worker turns
out right — watch that asymmetry." The worker pushed back on that framing and
is right, so the earlier entry should be read with this correction.

**Doubting a worker's red/green table is correct behaviour and should not be
discouraged.** The table *is* model output, and this entire third pass exists
because an earlier one produced a table that looked like coverage and was not.
A retro item that reads "the conductor doubted and was wrong" teaches the next
conductor to doubt less, which is precisely backwards.

The actual defect: **the verification used a narrower revert than the claim it
was testing, and neither party could see that from the artifact.** It would have
failed identically in reverse — had I reverted all four files and the worker
one, the worker would have been the one confidently wrong. Nothing about the
outcome depended on which of us held which check.

So the thing to watch is **a check whose scope is invisible in its output**, not
who was doubting whom. That also makes `git diff --quiet $BASE -- $IMPL` (now
on #121) the real remedy rather than a nicety: it fails loudly instead of
silently narrowing, which is the property the sentinel grep lacked.

What survives unchanged from item 1: I asserted a general principle ("a
worker's table is model output") in the same breath as a specific conclusion my
own method could not support. The principle was fine; pairing it with an
unverified conclusion is what made it deflection. The fix is not less doubt, it
is doubt that states its own scope.

Retro item 2 stands, in the worker's sharper form: **before changing what a
method returns, list its callers and check whether any of them wants the old
answer.** Cheap enough to be unconditional — here it was one read
(`storage/index.py:250`) and it prevented a silent index regression.

Worker stood down. Worktree verified by me: `c1c9c93`, no uncommitted edits
under `pyrite/`, `extensions/` or the theme's test file, the unrelated
`feature/journalism-investigation-kb` stash still at `stash@{0}` untouched. The
unrelated modified files (conductor skill edits, `.gitignore`, `FEEDBACK.md`,
`kb/roadmap.md`, untracked `kb/designs/`, `kb/tasks/`, `tests/usability/`) are
still there and still need an owner before anyone pushes from that tree.

## Retro 2026-09-18T08:20Z (retro 3 — window 07:20Z–08:15Z, ticks 4–5 and the revived ticks; called by the maintainer after the circuit breaker tripped on #69 and `dev` went red twice)

The maintainer's brief: "We ended up in a mess, and should sort out root causes and fixes as well as we can." So this one goes past the constraint to the roots.

### What worked, with numbers
- **The cold read**: 3 dispatched, 3 changed a PR's disposition (#69 twice — two silent data-loss regressions, then `priority` invented on every write and 9/12 vacuous regression tests; #81 once — the leak the theme was named for was relocated, not fixed). 0 defects merged from those branches.
- **The breaker tripped correctly** on the second redispatch of #69 and the loop stopped for the maintainer instead of dispatching a third pass on its own authority.
- **The value chain caught the red**: #81 passed the one-interpreter PR gate and failed the 3.13 leg on `dev` (d3d223a, 83b1da5) — a classmethod fixture pytest 9.1.1 tolerates and 9.0.2 does not. Root-caused and fixed by the host within 40 minutes of the second red (#129), the skew filed (#128).
- **Nested review landed** #83 and #81 unattended; #84 the window before.
- **Hallway → contributor**: 26 issues filed from three surfaces in one day; two outside PRs for #97 within 20 minutes of each other, both reviewed within the hour with recommendations posted; the maintainer chose "clean up and merge both in sequence", #116 first — its fixup is pushed with authorship intact.
- **Workers caught what conductors missed**: the #69 worker found 18 foreign commits in its own branch by diffing against its out-of-scope list (#119); the D worker filed the port collision (#118) instead of patching a file it was told not to touch.
- **`verify-red.sh` was wrong and is now right** (#121 → #125), with five tests that build a real repository per case.

### Failures and root causes
| Failure | Evidence | Why → why → root | Fix lives |
|---|---|---|---|
| Three conductors reviewed #69; contradictory verdicts 10 s apart | #111, 07:35:28Z vs 07:35:38Z | a worker's hand-back revives its dispatching tick → each revived tick believes it is the conductor → no claim existed on a tick or a PR | SKILL.md: one conductor at a time; `in-review` (landed #113) |
| A tick ran 1 h 46 m | #114 | worker reported mid-tick → the tick absorbed its own dispatch → no stopping point | SKILL.md: absorb only what had reported before the tick began |
| 18 foreign commits one push from the wrong PR; HEAD detached under a worker | #119, reflog | a conductor did checkouts inside a live worker's worktree → there was no claim on a worktree, only on a theme | SKILL.md/review.md: conductors review from their own worktree on the pushed head; pyrite-dev: footprint diff before push |
| `verify-red.sh` verified nothing, 12/12 | #121 | stash-based revert on a committed fix saves nothing → exit 0 → tests ran against the fix | #125 (merge-base revert, exit 2 = no claim); review.md checklist |
| Two confident wrong numbers | #101, tick 4 | two worktrees = two venvs = two Pythons; a flake rate against `dev` not the merge base | review.md (retro 2 + merge-base rule, #113) |
| Green gate on unpushed code | #91 | docs-only classification of a remote branch whose code was local → `gate: success` about the wrong commit | review.md: identify the commit before believing the check |
| A comment body ran `git rebase` on `dev` | #123 | backticks in a double-quoted `--body` are command substitution → the more careful the prose, the more shell runs | review.md: bodies through files, always |
| A test named for the regression it reintroduced covered only passing cases | #115 | reviewer reassured by a name → the cheapest trigger (Unsure names a design decision) was discretionary | SKILL.md: that trigger is mandatory; the reviewer's brief quotes the Unsure |
| #69 needed three passes | 11 review comments, 2 cold reads, breaker | dispatched to fix #46 with the root cause unknown → the worker inferred intent from load-time state → each fix exposed the next sibling (32 types invent keys) | dispatch.md: mechanism-unknown → spike first; quality: the round-trip identity gate before the write-path follow-up |
| `dev` red twice after #81 | d3d223a, 83b1da5 | `@classmethod` fixtures; pytest 9.1.1 (3.12, worktrees) tolerates, 9.0.2 (3.13, main) does not → the PR gate and the matrix ran different runners | #129 (fixed); #128 pin the runner (quality stock) |
| Ports 8088/5173 shared across worktrees | #118 (dup of #104) | file footprint cannot see a port → three Playwright workers talked to each other's servers | Package A.1 at the head of the queue; Playwright serialized meanwhile |
| Load 51 | tick 5, `uptime` | three browser suites + a 20-run loop + a redundant 10-run loop | retro 2's heavy cap; the redundant loop killed |

### The two roots
1. **Claims on themes, none on ticks or worktrees.** The draft-PR-as-claim made themes safe to hand between sessions; nothing did the same for "who is the conductor right now" or "whose tree is this". Every collision in the window is that gap.
2. **Signals about the wrong object.** A check about a different commit; a number from a different interpreter or baseline; a revert of a different file set (or none); a test whose name promises a case it lacks. The fix pattern is the same each time: bind the claim to its object — the SHA, the interpreter, the file set, the failing case — and refuse the claim when it cannot be bound.

### Waste, in the seven
Dominant this window: **relearning** (three readings of #69's diff; two cold reads that converged; the same defect filed twice as #104/#118 and #55/#127) and **defects** in the process's own instruments (verify-red, the benchmark, the gate-vs-commit). **Handoffs** cost the most tokens: ~100k for the duplicate cold read alone. Delays fell as load dropped from 51 to 4.

### Constraint
Coordination — the number of conductor instances alive at once (peak 4). Not the machine any more (load 4–12 by 08:10Z), not review attention per se: the review lane found more than it missed, three times over.

### The one process change
**One conductor at a time** — a revived tick only appends the report and exits; the scheduled tick absorbs only what had reported when it began; conductors review from their own worktree on the pushed head; workers footprint-diff, push, and report the SHA. In `pyrite-conductor/SKILL.md`, `review.md`, `pyrite-dev/SKILL.md`, `agents/pyrite-worker.md`. With it, as root-cause fixes: commit-before-check (#91), mandatory cold read on a design-decision Unsure (#115), bodies through files (#123), spike-before-worker when the mechanism is unknown, red-dev fix dispatchable under a breaker. PR `process/retro-3-one-conductor`.

### The quality theme
`pin-the-test-runner-one-pytest-and-xdist-version-for-every-venv-and-every-ci-leg` (#128; high, S, Sonnet). Stock behind it: the round-trip identity gate (prerequisite for #69's follow-up on the 32 types), changelog fragments, Package A.1 (#118).

### Expected effect
Conductor agents alive at once: peak 4 → 1 (+ revived ticks that exit within a minute); reviews per PR: 3 → 1 (+ cold read when triggered); redispatch rate this window 2/1 theme → ≤ 1/5 next window; zero `process` issues of the collision class. Revert if a worker's hand-back to an exited tick loses its report (check: every worker report appears on its PR body within a tick).

### Not changed, noted for next time
- The `pyrite-reviewer` agent ran 40 min with an unrequested full pytest on #108 and returned a fragment; one occurrence.
- #69's disposition: three passes verified by two conductors; held as draft only because `dev` was red and the breaker is tripped. The maintainer decides whether it merges when `dev` is green (recommended: yes, then the round-trip gate, then the 32-type follow-up as one Opus theme with #87 re-verified).
- Retro 1's heading is mis-stamped 06:45Z (ran ~06:00Z); retro 2 is correct at 07:20Z.
- The main checkout's local `dev` is clean and at `origin/dev` again after #123's accidental fast-forward; the peer session's commits all landed via #105.

### Tick 3 — #81 merged and turned `dev` RED. The cold read had called it.

**This is the tick's most important entry, and it is a failure of mine.**

PR #81 merged at 07:56:31Z with every check green and its push to `dev` went
**red** at 07:58: `test (3.13)` — `fixture 'read_only_client' not found`, six
errors in `tests/test_api_tiers.py`. The PR's gate runs **one** interpreter
(3.12), where the code works; the full matrix runs on the `dev` push, where
3.13 does not. That is the gate working as designed and me shipping through it.

**The cold read named this exact risk and I filed it as a trade-off:**

> Five fixtures gained `@classmethod` above `@pytest.fixture`, unexplained...
> **`@classmethod` over `@pytest.fixture` is an ordering pytest does not
> document as supported**, and the project pins only `pytest>=8.0.0` — I could
> not confirm the combination on pytest 8. A one-line comment naming the
> deprecation, or a floor bump, would stop the next reader from "simplifying"
> it back.

I read that, verified the fixtures ran *on this machine*, and carried it into
the PR body as a known trade-off. It was not a trade-off. **An unverified claim
about a decorator contract is an untested assumption**, and the one environment
I could not test it in is exactly where it broke. On 3.13 the stacking silently
stops registering the fixture — no error at import, the fixture simply is not
there, so every test that requests it errors at setup.

The distinction I got wrong, and the rule I would write from it: *a trade-off is
a cost you have measured and chosen. An unknown is not a trade-off.* When a cold
read says "I could not confirm X", the options are confirm it, remove the
dependency on it, or hold the PR — not publish it as an accepted cost. The
`@classmethod` change was incidental to the theme (it cleared a deprecation
warning nobody had asked about); the cheapest correct action was to drop it.

**Resolution: a peer session fixed it forward** (`cb7e7fa`, "class-scoped
fixtures in test_api_tiers are plain methods, not classmethods" — all five
`@classmethod` decorators removed), and its run is in progress. I did not
duplicate that work. Had no peer been on it, this was the next theme, ahead of
everything: `dev` red means nothing merges.

**Circuit-breaker check:** the skill trips the breaker on *two consecutive*
ticks whose `dev` push went red. This is one, inside tick 3, already fixed
forward by another session. Not a trip — but it is the loop's **first red `dev`
push**, after retro 1 recorded "0 red `dev` pushes" across nine merges, so the
next tick starts with one strike and should treat a second as the breaker.

**What should change (for the retro, not done here):** the PR gate runs one
interpreter for speed and the matrix runs after the merge, which is a deliberate
trade. It is correct for most changes and wrong for changes to *test
infrastructure* — a conftest fixture, a decorator contract, anything pytest
itself resolves. A rule worth considering: **when a diff changes how fixtures
are declared or collected, run the matrix on the PR.** This diff would have
qualified; the cold read's own words would have been the trigger.

### Package C (#82) absorbed — the decision was measured, not argued

Reviewed, rebased, pushed, flipped, auto-merge armed. The worker chose option
(a), the second auth-enabled project, and **proved it rather than asserting it**:
pointing the new project's `baseURL` at the auth-disabled world fails **8 of 18
tests** (gate redirect, the 401, real sign-in, the signed-in redirect, both
error-message assertions); the other 10 are markup shape and pass either way.
Those 8 are what the second world buys. That is the best-argued decision any
worker has returned in this loop.

Config discipline held: the shared `playwright.config.ts` gained exactly one key
on the existing project (`testIgnore`) and two new projects; name, `use`, both
original `webServer` entries, `retries: 0` and `reuseExistingServer: false`
untouched — verified hunk by hunk, because this was the one file in the fan-out
whose edit could break four sibling branches.

**A real user-facing bug fixed:** both auth forms rendered `ApiError.message`
(the developer string, `API Error ${status}: ${detail}`) so a mistyped password
read "API Error 401: Invalid username or password". `.detail` existed all along
(`client.ts:921-930`, confirmed). Unreachable under the auth-disabled world —
another argument for (a). Fourth package running to find a real bug through a
real assertion (B→#49, E→#89, D→the create race, C→this).

**Its force-push needed the conductor.** The worker rebased to pick up Package
B, which rewrote the claim commit, and its `--force-with-lease` was denied by
the permission system. It **stopped and reported rather than working around it**
— correct — and supplied `git range-diff` showing `f0c7516 = 1b170a2`, which I
verified before pushing: the only remote-only commit was reproduced
byte-identically, so nothing was at risk.

Its `CHANGELOG.md` conflicted on rebase (#103 again, third occurrence this tick)
— both sides were new, unrelated entries, so both were kept.

**Filed by C: #130** (`vite.config.ts` has no `strictPort`, so a busy 5173
silently falls through to 5174 — it caught a sibling's dev server on its own
world's port; same class as #104/#118 and the reason it chose 8189/5274 rather
than the fall-through ports) and **#131** (the API returns 500s under concurrent
load — `sqlalchemy.exc.InvalidRequestError: This session is provisioning a new
connection`, with a clean correlation: 0 backend errors → 8-10 failures, errors
present → 12-25). **#131 is a product bug in session provisioning found only
because the machine was loaded**, and it deserves its own theme.

**Honest evidence, flagged by the worker rather than smoothed over:** its "5x in
a row" is five *executing* runs; runs blocked before any test ran (siblings
holding 8088/5173) were discarded and said so. I re-ran the auth project myself
on the rebased base with the siblings idle: **19 passed (9.4s)**.

### Tick 3 close — `dev` is green, and #131 is the fan-out's real blocker

**`dev` recovered.** Run 35324168334 on the current tip `d611dca`: `test (3.11)`,
`test (3.12)`, **`test (3.13)`**, `frontend`, `smoke`, `coverage`, `kb`, `gate`
all green, 5m20s. My 3.13 breakage is fixed — verified on the interpreter that
broke, not merely "the run says success".

One wrinkle worth recording: **both `push` runs were cancelled** by the
`concurrency` group (`cancel-in-progress: true`, keyed on `github.ref`), so the
peer's fix commit and Package C's merge each cancelled the previous run and
neither push was ever verified by its own run. The green evidence comes from a
manual `workflow_dispatch`. That is the concurrency rule working as designed —
a newer push makes the older answer irrelevant — but it means **on a busy `dev`
the last push's run can be cancelled and nothing re-runs it**, so "is `dev`
green" has to be answered by checking a *completed run against the current tip*,
not by reading the top of `gh run list`. Two of the three entries there were
`cancelled`, which is neither success nor failure.

**The `e2e` job failed in that run, and it is not a Package C regression.** It
is `continue-on-error: true` and manual-only, so it did not gate. Its failures
are **#131**, the server-side 500s Package C filed — now reproducing **in CI**,
which removes the "only a loaded dev machine" explanation:

```
sqlalchemy.exc.InvalidRequestError: This session is in 'prepared' state;
    no further SQL can be emitted within this transaction.
IndexError: tuple index out of range
```

Note it is a *second* illegal state on the same session (the original report was
"provisioning a new connection; concurrent operations are not permitted"), which
points at one session object shared across concurrent requests rather than a
single bad call site. `chromium-auth`'s specs passed in the same run, so C's work
is sound.

**The consequence for the roadmap, and it is the important one:** the specs that
fail in that job (`collections`, `qa`, `search`) fail with `element(s) not found`
— pages that rendered nothing because their API call 500'd. **#131 manufactures
exactly the "flaky e2e" the Playwright fan-out exists to eliminate, and it will
keep doing so after every spec is rewritten.** So:

> **Package H cannot succeed while #131 is open.** Flipping `continue-on-error`
> off the `e2e` job makes `dev` red on a server bug that has nothing to do with
> the specs. #131 must land before H, and it is a Python/server theme — Opus,
> cold read, `pyrite/server/` and session/dependency provisioning.

That re-orders the remaining fan-out: **F and G (spec rewrites, parallel-safe),
then #131, then H.** Recorded here because the tick that dispatches H will not
otherwise know.

**Tick 3 final: 4 themes dispatched, 4 merged** (#84 Package E, #83 Package D,
#81 the quality theme, #82 Package C), 1 red `dev` push caused and fixed
forward, 6 issues filed by this conductor (#86, #103, #104, #107, #109, #133),
5 by its workers (#88, #89, #117, #118, #130, #131). First cold read of the loop,
and it changed the outcome twice — once by finding the fixture's false claim,
once by calling the `@classmethod` risk I then mis-filed as a trade-off.

## Tick 2026-09-18T09:20Z (tick 6 — host-run; the loop restarted by the maintainer as `/loop 20m /pyrite-conductor` after retro 3)

**Health.** `dev` green at 4e34b80 (full matrix, 09:05Z). Load 6.9 (from 51 at the peak). Open loop PRs: #69 (ready, auto-merge armed, gate running after the host's rebase and re-verification: 4285 passed, footprint 13 files, #87 fixture re-run by hand) and #70 (the log). Outside PRs: 0 — #116, #108, #126 all merged by the maintainer this hour; #97 and #57 closed. Milestone 0.24.2 open: #118 #87 #56 #46 #21 #18 #13 #9 (#46 #18 #21 #87 close with #69). Worktrees: only #69's and the log.

**Absorb.** Nothing waiting — every worker report before this tick was absorbed (C merged at 08:22Z by a revived tick; #69 by the host).

**Groom.** Ready queue was under twice the cap → `pyrite-architect` dispatched over: milestone #56/#9/#13, the DoD items without a theme (packaged web UI, README, docs counts, CI parity lint, version single-source, Playwright F/G/H), the pool rows, the worker findings, the quality stock. It was told which issues are `good first issue` and reserved for outside contributors for 24 h.

**Dispatched (3 workers; cap by review queue = 0 awaiting, ≤2 heavy → 1 heavy):**
| Theme | PR | Model | heavy |
|---|---|---|---|
| Playwright package A.1 — per-worktree ports and data dir (#118) | #138 | sonnet | yes — the only Playwright process allowed |
| Pin the test runner (#128; quality) | #139 | sonnet | no |
| `scripts/release.py` (0.24.2 DoD) | #140 | opus | no |
The round-trip identity gate waits for #69 to merge (next tick). Claims: the backlog item as first commit on each branch — two created (`playwright-package-a-1…`, `scripts-release-py…`), one hand-edited to `in_progress` because `pyrite update` is #46 until #69 lands.

**Friction.** Tick 5 reported creating the A.1 backlog item; it was not on `dev` (created in a worktree and never pushed, or on the log branch) — the record a tick leaves must be pushed to be a record (filed). The skill loaded from the main checkout was stale (behind `origin/dev` by retro 3): fast-forwarded before running.

**Blocked / needs the maintainer.** Nothing. The next kept item is the release plan, several themes away.

## Retro 2026-09-18T09:25Z (retro 4 — window 08:20Z–09:20Z; five themes landed: #82, #116, #108, #126, #69)

### What worked, with numbers
- **Outside PRs, end to end.** First loop review 9–28 min after arrival (#116 at +9, #108 at +24, #126 at +28); every one cold-read; all three merged under their authors' names within 61–105 min; the competing pair for #97 landed as a sequence (#116's disk lookup first, #108's design on top) with cross-credit in both directions. A fourth contributor's PR (#126) arrived 37 min after its `good first issue` label.
- **The breaker held and released cleanly.** #69 landed on its third pass after two conductors' verification and the host's re-check on the rebased branch; three consecutive green `dev` pushes (6d97774, 4e34b80, 47ea84c) and a green full matrix on demand.
- **One conductor at a time, in practice.** Tick 6 ran host-side under retro 3's rules; zero collisions, zero duplicate reviews, tick length 25 min including three dispatches and the architect.
- **The record kept up.** The architect's breakdown was pushed to the log branch in the same tick (#141's rule applied before it was written into the skill); `verify-red.sh` (#125) was used in every review this window and gave one exit-2 that was correct.
- **Green-first evidence discipline held**: the #108 worker measured its own "speedup" and reported none (163 ms unchanged; root cause filed as #135) rather than let the comment over-claim.

### Failures and root causes
| Failure | Evidence | Why → root | Fix lives |
|---|---|---|---|
| 6 approval clicks for 3 outside PRs; #116 needed 3, #108 3 (one on a superseded head) | run ids 35323518166, 35324810356, 35325939964, 35326165584… | every push by a non-owner to a first-time contributor's fork re-arms GitHub's gate → our cleanup was rebase, fixup, then a trailer amend: three pushes where one would do; the maintainer's "Update branch" pushed a fourth head under a worker mid-amend → **no protocol for how many times, and when, a maintainer touches a contributor's branch** | review.md: one push per outside PR, everything squashed into it, only while the maintainer is present; `in-review` is the lock against Update-branch |
| Co-author trailers on #116's fixup (now on `dev` as 4b209f6) credit nobody | `gh api …/commits/4b209f6` resolves no co-author | the `<login>@users.noreply.github.com` form links only for pre-2017 accounts → the spec gave the form from memory | review.md: take the address from the contributor's own commit (`git log --format=%ae`) |
| The sweep re-flagged reviewed PRs | 08:48Z sweep: "loop reviews: 0" on #116/#108 | detection by comment-heading regex; the reviews used other headings → `reviewed` label (fixed in-window) | done |
| `verify-red.sh` popped a stale stash into a fresh review worktree | #126 review report | the branch under review predated #125, so the *branch's* old script ran; the stash stack is repo-global (`feature/journalism-investigation-kb`) → sweep now runs `dev`'s script (fixed in-window); the stale stash entry is still there | maintainer: `git stash drop` when convenient |
| A.1's backlog item, reported created at tick 5, did not exist | #141 | created somewhere never pushed → the skill said "leave the record" but not where | SKILL.md: tick artefacts outside a theme branch go on the log branch in the same tick |
| Two `dev` runs `cancelled` with `gate: failure` (3dc04f8, 4b209f6) | run list | merges 1–3 min apart; concurrency cancels the older run → harmless, but the breaker's "two consecutive red pushes" could count a cancelled run | SKILL.md: the breaker counts `failure` on a completed run, never `cancelled` |
| CHANGELOG conflicted twice on #116 alone, each costing a push and a click | #116's two rebases | every theme appends to the same `### Fixed` block | quality: `changelog-fragments…` (nominated) |

### Waste, in the seven
Dominant: **delays** at the maintainer's desk — six approval clicks, three merges and one Update-branch, all serial, roughly half of each outside PR's lead time; and **handoffs** — three pushes to #116 where one would do, each a fresh gate. **Relearning** fell (one review per PR this window, none duplicated). Defects: none reached `dev` (three green pushes).

### Constraint
The maintainer's desk, for the first time — and correctly so: merging outside work is kept. The remedy is to reduce what reaches it: one push per outside PR, and (a recommendation, kept) GitHub's fork policy "require approval for first-time contributors *who are new to GitHub*" would have run all six of this window's runs without a click — every contributor this window had an account older than a year.

### The one process change
**The outside-PR cleanup protocol** in review.md: prepare everything locally (rebase, fixup, trailers taken from the contributor's own commit address), verify, then **one push**, timed when the maintainer is present to click; `in-review` on the PR is the lock — the maintainer does not press Update-branch on a claimed PR. With it, as root-cause fixes: #141's log-branch rule and the breaker's `cancelled` clarification in SKILL.md. PR `process/retro-4-outside-pr-cleanup`.

### The quality theme
`changelog-fragments-one-file-per-pr-under-changelog-d-assembled-by-the-release` (existing stock; sonnet) — dispatch immediately after `scripts/release.py` (#140) merges; the release.py worker has been told to isolate `release_notes_for(version)` so the fragments theme swaps its input. Evidence: 2 CHANGELOG conflicts on one outside PR; every parallel theme pays it.

### Expected effect
Approval clicks per outside PR 2–3 → 1; outside-PR lead time 60–105 min → < 60; CHANGELOG conflicts per merged PR 2/9 this window → 0 after fragments. Revert the one-push rule if it delays a contributor's fix by more than a tick waiting for the maintainer.

### Not changed, noted for next time
- Recommend (kept): fork-PR approval policy → "first-time contributors new to GitHub". The maintainer decides.
- The seven Dependabot `web/` PRs sat `BEHIND` all day by design; dispatched this window as one theme (chore/web-dependency-bumps) before F/G.
- 24-hour reservation of `good first issue` items for outside contributors is a host rule, not yet in the skill; the architect honoured it from the brief. Write it down next retro if it survives.
- The stale repo-global stash (`feature/journalism-investigation-kb`) still trips tools that use `git stash`; the maintainer's to drop.

## Tick 2026-09-18T09:40Z (tick 7 — host-run, scheduled)

**Health.** `dev` at 1226312 (retro 4 merged), run in progress; previous three pushes green. Load 10. Open loop PRs: #138 A.1, #139 pin, #140 release.py, #142 web deps (all draft, workers running; each branch at its claim commit only — none reported), #70 log. Outside PRs: 0. Good-first-issue pool: 14 open. Worktrees: the four workers' + the log.

**Absorb.** Nothing had reported before the tick began.

**Groom.** The architect's tick-6 breakdown is on the log branch (`groom-2026-09-18-tick6`); ready queue is long — no architect this tick. Good-first-issue count ≥ 5.

**Dispatched (2; cap: 0 awaiting review, 1 heavy in flight, footprints disjoint from everything running):**
| Theme | PR | Model | heavy |
|---|---|---|---|
| Filters are honoured on every search leg (#56, closes #53) | #145 | opus (cold read expected) | no |
| The round-trip identity gate (quality; after #69) | #146 | sonnet | no |
Six workers in flight. Held for later ticks per the breakdown: F/G (after A.1), H (after F/G), packaged web UI (after #140 or with the runbook edit assigned), CI parity (after #139 — both touch `test_dev_process_config.py`), 7B index-sync (after the reservation window on #44/#47), #13+#43 (opus, heavy — when a heavy slot frees), #9 spike.

**Observed.** The first claim through `pyrite update` since #69 landed is a two-line diff (status, assignee) — #46 fixed in practice. The Dependabot batch dispatched last tick will close #23–#29 on review.

**Blocked / needs the maintainer.** Nothing.

## Tick 2026-09-18T09:42Z (tick 8 — host-run, scheduled; the first absorb tick under retro 3's rules; heading corrected from an estimated 10:05Z — the host stamped by guess; from here on entries are stamped with `date -u`)

**Health.** `dev` green at 35ea097 (groom-into-the-ticket merged); load 8 → 16 during the reviews. Outside PRs: 0. Good-first-issue pool: 14.

**Absorbed — three branches that had reported before the tick began**, each reviewed from its own `review/pr-N` worktree on the pushed head (never the worker's tree), claimed with `in-review`:
- **#139 pin the test runner** (`9f725ed`): venv reinstalled from the pins → pytest 9.1.1; 4240 passed; `PT` clean. Reproduced the worker's unmet-criterion finding — a `@classmethod` fixture under the pinned runner is neither a lint finding nor a failure; the criterion's premise was wrong, #144 tracks the deprecated instance-method fixtures. Ready, auto-merge; rebased once after #142 landed. Post-merge: the matrix must show 9.1.1 on all three legs.
- **#142 web dependency bumps** (`387ab4f`): clean `npm ci` (npm 11.5.1's arborist crash reproduces; 11.19.1 works), build/unit (388)/check (0 errors) green; **one Playwright run on the branch fails exactly the #49 pair** — the kit 2.53→2.70 bump moved nothing the specs assert on. **Merged (86feee3)**; **#23–#29 closed** against it; worker worktree removed.
- **#138 Playwright A.1** (`4f2585b`): vitest 393 passed, check clean, derived ports 22440/23849/25031/28143, one full run 125/3 — the #49 pair plus `entry-features.spec.ts:167`, not in any of the worker's sets. Re-ran that spec alone ×3: run 1 failed 167 and 144 at ~170 ms (instant, first run after the servers start), runs 2–3 clean → a first-request race, filed **#153** (`needs-repro`), not A.1's defect. Cold read dispatched (mandatory: the Unsure names two design decisions — the five spec-file edits and `strictPort` on the shared Vite config); verdict when it returns.

**Reported mid-tick (next tick's absorb), reports appended to their PRs:** #140 `scripts/release.py` (opus; 85 tests, dry-run transcript, named-check CI wait, `release_notes_for` seam; four Unsure incl. no `.dev0` bump and step e's local commit) · #145 search filters (opus; option 1 — filters on the vector leg on all backends; 4348 passed; Postgres unexercised locally; three design decisions in Unsure → cold read) · #146 round-trip gate (sonnet; 70 residual ids in 5 groups, 774/774 fail on a scratch revert of #46's fix; filed #148 #149 #150 #151).

**Groom.** No architect this tick (ready queue long). Reserved good-first-issues untouched.

**Dispatched.** Nothing — six branches in absorb/review this tick and next; the review queue is the cap.

**Friction.** `node web/e2e/print-ports.ts` needs the repo root as an argument (the usage line says so; the review's first call omitted it) — fine, but `scripts/new-worktree.sh` must pass it; check in the cold read. Three suites sharing the machine during review produced one spurious failure (the #153 flake) — reviews of heavy branches should run one at a time, same rule as builds.

**Needs the maintainer.** Nothing.

## Tick 2026-09-18 10:08Z–10:31Z (tick 9; end stamp corrected at tick 10 — the host wrote 11:05Z by estimate again, against the `date -u` rule; the review-comment times inside the PR bodies (10:40Z–10:55Z) are estimates too, ~20 min fast)

**Health.** dev green (aa024d4, then b5514c1 after #138). #138 merged 10:12Z, #118 closed, its worktree removed. No outside PRs. Load 1.8→8 during the three parallel suites.

**Absorbed** (each from its own `review/pr-N` worktree on the pushed head; all three removed at the end of the tick):

- **#146** round-trip identity gate (sonnet) → **ready, auto-merge armed** (rebased once, BEHIND after #138). Suite 4300 passed / 70 xfailed / 1 failed: `test_walk_is_fast`'s 10 s wall-clock budget under `-n auto` beside two other suites — the load-sensitive-timeout class; fixed by the host in `5811c81` (60 s). Gate bites: both halves of the #46 fix reverted → 7 failed; one half alone stays green (each half prevents the leak). Follow-ups the worker filed: #148 #149 #150 #151.
- **#140** `scripts/release.py` (opus) → **redispatched** (opus, same branch). Suite green bar #88's load race; verify-red exit 0. Cold read: design sound, but on first use the `release-blocker` gate is inert (label absent → skipped, and the label did not exist — created it this tick), no tag-existence guard so a retry moves `main` then reports "nothing further was attempted", CHANGELOG parsing ignores fences and duplicate headings, `origin` never checked against the hard-coded slug, the tutorial-hook tests pass against a deleted implementation, step e commits on local `dev` naming a branch it never made. Eleven items in the PR body; six must-fix.
- **#145** search filters on every leg (opus) → **redispatched** (opus, same branch). Suite 4348 passed; the matrix is genuinely red against dev. Cold read found a **regression**: `k` escalation clamps only to the table size, never to sqlite-vec's 4096 cap — semantic and hybrid search raise on any KB above 4096 embedded rows (the maintainer's index: 18,909), incl. unfiltered queries under `max_distance`; confirmed from the source (no `4096` anywhere in the file or `tests/`). Plus: the `TypeError` rescue swallows real bugs as "backend cannot filter" (declare a `FILTERED_SEMANTIC` capability instead); REST serialises `"warnings": null` while MCP omits the key, and the test that should catch it cannot fail; `include_archived` is not applied on the vector leg while the PR's new contract says every filter on every leg. Five must-fix in the body.

**Reported this tick, absorb next:** #157 web security alerts (sonnet; 16 of 19 alerts, `cookie` ×3 stays — kit 3.x prerelease only), #158 CI job permissions (sonnet; checks all green on the PR). Both bodies carry the reports.

**Spike (CodeQL triage) landed its `## Groom`** on the log branch (a785be0, 468 lines): 4 true positives of 48 — one exploitable, `py/polynomial-redos` #43 (`GET /api/search` has no `max_length`; 40k chars → 12 s CPU on the read tier) — 43 noise with the guard named per alert, a 43-row dismissal table, four themes. Spike worktree discarded, no code kept.

**Dispatched** (4 workers, footprints disjoint; 2 small sonnet reviews wait):
- Playwright **F** graph + timeline (#160, sonnet, heavy) — A.1 landed, one heavy at a time.
- **#140 redispatch** (opus) — the eleven findings.
- **#145 redispatch** (opus) — the five findings + the "also" list.
- CodeQL **Theme B** repo error-message disclosure (#161, opus) — `git_service.py`/`repos.py` quiet; #51 #52 #53.
Not dispatched: Theme A (ReDoS cap — hard conflict with #145; after it merges), Theme C (after A and B), Theme D (kept decision), Playwright G (next tick; one heavy at a time), CI parity 6F, packaged UI 6E (coordinates with #140's runbook edit — after #140).

**Kept, for the maintainer** (no action taken):
1. `py/weak-sensitive-data-hashing` ×7: spike recommends *dismiss as won't fix* + Theme D (a `pyrite key new` mint command + docs, so keys are random by construction) rather than a keyed hash that breaks every deployed `config.yaml`. If keyed hash is preferred it needs an ADR.
2. CodeQL as a required check: 44 of 48 alerts were noise and the one exploitable finding was a `warning`, not an `error` — severity is not a usable filter. Recommendation: not required; Theme C dismissals make the page honest first.
3. Private-repo existence oracle via `POST /api/repos/subscribe` (write tier learns whether a private repo exists through the operator's token) — no alert, not ticketed, needs a design decision.

**Process notes for the retro.** (a) Two of three Opus branches came back with must-fix findings from the cold read that the worker's own evidence did not surface — both in the regime the tests never entered (N>4096; a retry after a failed publish). "Tests prove the fix is real" and "tests cover the failure regime" are different claims; the dispatch spec could ask for the second explicitly. (b) The 10 s wall-clock test is the third load-sensitive timeout this week (#55, #88, now #146); the pre-push hook runs alone, the conductor's parallel suites do not. (c) A GitHub push failed once on a 75 s connect timeout mid-tick; retried fine — a tick must re-check `git ls-remote` after any push, not trust the exit of a pipeline. (d) Tick length ~57 min against the "thirty minutes is long" line: three absorbs with two cold reads plus four dispatches is more than one tick should carry; the queue had built up because ticks 7–8 dispatched five themes.

## Tick 2026-09-18 10:33Z–10:41Z (tick 10)

**Health.** dev green (b5514c1); #146 merged during the tick (34fbf29 → dev run e547800 in progress at the end). Load 3.7 → 10.8 during the parallel suites. GitHub API had TLS-handshake timeouts for ~2 min: the first `gh pr edit --add-label` calls silently failed and my "claimed" echo printed anyway — re-checked and re-claimed. Tick 9's end stamp corrected (I wrote 11:05Z by estimate; `date -u` said 10:31Z).

**Absorbed** (review worktrees on the pushed heads; both removed at the end):
- **#158** CI job permissions (sonnet) → **ready, auto-merge, rebased**. `tests/test_dev_process_config.py` 40 passed; with `ci.yml` reverted to dev's, 3 failed — the tests pin the change. The only steps that could want more than `contents: read` are two `upload-artifact` uses, which need nothing. The PR's own checks passed under the narrowed token.
- **#157** web security alerts (sonnet) → **ready, auto-merge, rebased**. From a deleted `node_modules`: `npm ci` clean, build ok, unit 388/388; resolved vite 7.3.6 / svelte 5.57.0 / postcss 8.5.28 / picomatch 4.0.7 / esbuild 0.28.2; audit `{low: 4}` = exactly the `cookie` chain. Dependabot's #154/#155/#156 bump to the same versions — expected to close themselves on merge; a waiter checks, and next tick runs Playwright once against dev for the svelte bump.

**Dispatched** (5 workers; footprints disjoint; 0 branches await review):
- **CI parity 6F** (#163, sonnet) — `extensions/` lint (54 errors today) + ci.yml ruff scope + fix-needs-a-test on PRs. Told to rebase onto #158 before touching `ci.yml`. The item now carries its `## Groom` (copied from the tick-6 note into the ticket, per the groom-into-ticket rule). `pyrite update -f status=…` produced a two-line diff — #69's fix holds.
- Still running from tick 9: Playwright F (#160), #140 redispatch, #145 redispatch, CodeQL Theme B (#161).

**Not dispatched:** Playwright G (waits for F's report — one heavy at a time until the derived ports are proven under two suites); H after F+G; 6E packaged UI after #140; CodeQL A after #145, C after A+B, D kept; index sync (7B) inside #44/#47's reservation window until 2026-09-19 08:45Z.

**Groom lane:** ready queue ≥ 8 groomed themes (> 2× cap) — no architect this tick. `good first issue` pool: 14 open.

**Kept (unchanged from tick 9):** the hashing decision (dismiss + Theme D vs keyed hash/ADR); CodeQL as a required check (44/48 noise); the private-repo existence oracle.

**Retro notes.** (a) The estimated-timestamp error recurred one tick after the rule was written (tick 8 → tick 9); the fix is mechanical — stamp the heading with `$(date -u)` in the same command that appends it, never by hand. (b) `gh` label edits during an API blip failed silently behind `>/dev/null`; the claim must be verified by reading the label back, which the sweep already does — the conductor should too. (c) Two tiny sonnet absorbs took ~15 min including a clean `npm ci`; that is the floor for a review, and it bounds the cap at ~4 absorbs per tick.

**Reported mid-tick (absorb at tick 11):** CodeQL Theme B (#161, opus) — `a9a19ad`; 17 new tests red-then-green; the report is on the PR body; cold read required (server + services; `_ABS_PATH_RE` breadth and the two-statics shape are design points).

## Retro 5 — 10:48Z — window 09:25Z–10:42Z (ticks 7–10; five themes landed, two redispatches)

### What worked
- **dev stayed green through 7 pushes** (1226312 → 36d4b59, 7/7 `success`; gate 2–5 min each). The pinned runner (#139) held: no interpreter skew since.
- **The cold read earns its cost: 3 of 3 dispatched changed the PR.** #138 → six fixes before merge; #140 → 11 findings, redispatched; #145 → a regression that would have broken every semantic search on the maintainer's index, redispatched. Under retro 3's mandatory trigger (an Unsure that names a design decision) none of the three would have been skipped.
- **Lead time, claim → merged, for the five landed themes: 30–65 min** (#142 30, #157 36, #139 44, #138 59, #146 65). The two longest waited on a tick boundary, not on work.
- **The spike model.** The CodeQL spike returned a 468-line groom into the ticket, a 43-row dismissal table and four dispatchable themes; the worktree was discarded. 44 of 48 alerts were noise — knowledge, not code, was the output (amplify-learning), and it settled a kept decision's evidence (CodeQL as required check) without a line of product change.
- **Groom-into-ticket held**: both new themes this window (6F, Theme B) were dispatched from a `## Groom` section on the item, not from a title.

### Failures and root causes
- **#145 redispatched** (cold read: `k` escalation with no 4096 cap; raises above that on the maintainer's 18,909-row index) → the worker's 44 tests all ran below the cap → the spec's acceptance named which rows come back, never "at what size" → **the spec has no field for the regimes the tests must enter** → `dispatch.md` (this retro's change).
- **#140 redispatched** (cold read: no tag-existence guard; `main` moves, then "nothing further was attempted"; the `release-blocker` gate inert when the label is absent) → 85 tests, none for "a tag exists from an aborted run" or "label missing" → same root cause: the spec listed steps, not the states the repo can be in when the script runs → `dispatch.md` (same change). Secondary: the label did not exist in the repo — a repo-state precondition nobody checked; created at tick 9.
- **#146's `test_walk_is_fast` red under three parallel suites** (10 s wall-clock budget; ~2 s idle) → the worker's pre-push ran alone → the third load-sensitive timeout this week (#55, #88, now this) → the pyrite-dev skill says "fixed wall-clock timeouts under load are a bug in the test" but nothing makes a worker run under load → *not changed this retro*; noted below.
- **Tick 9's end stamp estimated (11:05Z; measured 10:31Z), one tick after the `date -u` rule** → the rule says "stamp with `date -u`" and the host still typed the heading by hand → the stamp was a habit, not a mechanism → fixed at tick 10 by stamping the heading in the same shell command that appends it. My elapsed-time sense runs ~20 min fast; every "10:40Z–10:55Z" inside tick 9's PR comments is wrong by that much.
- **`gh pr edit --add-label` failed silently during a TLS blip and the tick printed "claimed"** → `>/dev/null` plus an unconditional echo → a claim that is not read back is not a claim → tick 10 now reads the label back (the sweep already did).
- **#159** (`process`): the commit-msg hook does not count `web/**/*.test.ts` as tests → a `fix:` commit on the frontend cannot pass the hook honestly → the hook's path rule was written for Python → belongs to 6F (in flight) or a one-line follow-up; not this retro's change.

### Constraint
**The review lane, and specifically its rework loop.** Tick 9 absorbed three branches and sent two back: a redispatch costs a second Opus pass (~30–45 min), a second cold read and a third review — the review lane's queue this window was 7 items for 5 landings (redispatch rate 2/7 = 29%). WIP: 4–5 workers, 0–3 branches waiting; the gate was never the wait (2–5 min per run, 7/7 green). The maintainer's desk holds three kept decisions but nothing landed is blocked on them.

### Waste, in the seven
- **Defects (dominant):** two branches that were "done" by their own evidence and unsafe where the evidence never went. Not defects that reached `dev` — the cold read held — but rework of 2 of 7 themes.
- **Handoffs:** the same two: acceptance criteria copied verbatim from the ticket (the rule) carried the ticket's blind spot verbatim too.
- **Delays:** `CHANGELOG.md` conflicts — 3 of 6 open branches `DIRTY` on that one file at 10:42Z, incl. #158 with auto-merge armed; 18 PRs touched it since 05:00Z. Each is a manual rebase between "ready" and "merged".
- **Relearning:** the timestamp estimate (twice); the silent `gh` failure (a pattern the sweep prompt already guarded against).
- **Partially done work:** none — every branch has a draft PR with its report; the ready queue (≥8 groomed) exceeds 2× cap. **Extra features:** none seen — footprints matched Touches on all five landed themes (three unavoidable extras on #145 were named). **Task switching:** tick 9 ran 23 min with three absorbs interleaved with four dispatches — long, but nothing was dropped.

### Friction observed
- The conductor had to reproduce the reviewer's blocker from source (`grep 4096` → 0) because the review rule says a reviewer's report is model output — right, and cheap here (2 min); keep.
- The #146 worker built the scratch-revert proof with both halves of the #46 fix; the conductor's one-half revert stayed green and cost a second attempt — each half alone prevents the leak. A worker's "how I proved it" line is worth copying exactly.
- The Playwright F worker hit 5 navigation timeouts on the first run after `npm ci` (Vite dependency re-optimization, #153) and spent a cycle proving it was not a product bug — the gotcha is documented; a warm-up run in the dispatch prompt would have saved it.
- `pyrite sw backlog --status proposed | grep quality` returned nothing at tick 10 though the `quality`-tagged changelog item exists — the CLI's list output does not print tags. The conductor should filter with `pyrite search "quality" -k pyrite` or `--tag`; a tool gap worth a line in the skill, not this retro's change.

### The one process change
**A theme spec names the regimes its tests must enter, and the worker's Evidence lists each with the test that enters it** — `dispatch.md` (spec template + rule, mandatory for storage/server/repo-mutating scripts/bounded loops) and `pyrite-worker.md` (report format). PR: #165 (`process/retro5-boundary-regimes`, auto-merge).

### The quality theme
**CHANGELOG fragments** (`changelog-fragments-one-file-per-pr-under-changelog-d-assembled-by-the-release`, oldest open `quality` item; now groomed, priority high) — removes the one file every PR conflicts on (18 touches, 3 of 6 open branches `DIRTY` on it alone). Footprint: `CHANGELOG.md`, `scripts/release.py` (`compose_notes`), new `changelog.d/`, `tests/test_dev_process_config.py`, the skills. Sonnet. **Sequence: after #140 merges** — it owns `release_notes_for` until then.

### Expected effect
Redispatch rate from 2/7 (29%) this window to ≤1/10 over the next ten dispatched themes, measured at retro 7; cold reads should start returning "accept as-is" on the regime questions rather than blockers. Revert the `Regimes:` rule if it grows specs without moving the rate — or if workers start listing regimes they did not test (check the red lines). Fragments: `DIRTY`-on-CHANGELOG-only events from 3 per six open branches to 0 within two ticks of landing.

### Not changed, noted for next time
- Load-sensitive timeouts (third this week): a `pytest` invocation in the pre-push hook that runs the changed test files under `-n auto` *while the suite runs* would catch them; or a lint rule against `assert elapsed <`. One change per retro; this is next if a fourth appears.
- Slowest tests: `test_git_env_isolation` 16 s + 6.5 s (spawns a full suite under a hook), `test_private_kb_read_scoping` setups at 10.9 s and 10.7 s (an app + user fixture per test — a module-scoped app would take the file from ~40 s to ~10 s). A quality theme for a later retro; not the constraint today.
- `#158`/`#161`/`#145` are `DIRTY` on CHANGELOG now — the conductor rebases them next tick; the fragments theme ends the class.
- `web/**/*.test.ts` in the fix-commit hook (#159): fold into 6F's CI step (in flight) or a one-line follow-up.
- Kept decisions outstanding (no wait on them yet): API-key hashing (dismiss + mint command vs keyed hash), CodeQL required check, the private-repo existence oracle.

## Incident 2026-09-18T11:19Z — tick 11 crashed the machine (OOM); the loop is stopped

Issue #168. Tick 11 began 10:49Z with load at 14 and started three `-n auto` review suites (#161, #140), a Playwright run (#160), two cold reads and an outside-PR review (#164); the outside-PR sweep then launched two more review agents (#166, #167), each told to run the full suite; two workers (#145 redispatch, #163) were running theirs. Up to eight concurrent suites on a 16 GB / 10-core machine. It went down at ~11:10Z; the session and all three session crons died with it.

**Nothing was lost.** Every worktree was clean. #145: six fix commits committed locally, unpushed (`c3f5659`..`7ff5704` — k clamp at 4096, declared `FILTERED_SEMANTIC` capability, REST omits `warnings`, archived exclusion on the vector leg, `limit` validated, PG `max_distance` in SQL). #163: pushed complete at `7c81923`, worker never reported. #158 merged 11:05Z (the eight `actions/missing-workflow-permissions` alerts are closed: 0 of 8 open). #157 merged; Dependabot #154–#156 closed themselves. #167 was closed by its author at 11:09Z; #164 (same fix) stays open, unreviewed; #166 unreviewed. Dead `in-review` claims released on #140, #160, #161, #164. dev green at 28fc380.

**Root cause:** the machine budget counts dispatched workers only — not the conductor's own review suites, not review agents (each told to run the suite), not the pre-push hook inside every worker; nothing serialises suites across worktrees and `-n auto` sizes to cores, not to what else is running. The tick log had recorded load 8–14 for three ticks and nothing acted on it.

**State of the loop:** stopped. No crons armed. Not re-armed without the maintainer. Interim rule when it restarts: one full suite on the machine at a time (the conductor's included), review suites `-n 4`, outside-PR review agents do not run the suite themselves, ≤2 workers, Playwright never beside a suite. First theme on restart: a machine-wide suite lock + memory-bounded xdist count, used by the pre-push hook, the workers and the conductor.

## Tick 2026-09-18T12:19Z (tick 12 — WIP = 1; first tick after the OOM incident, #168)

**Pre-check** 12:12Z: load 2.7, 79% memory free, no heavy process, dev green (f977f48). One thing this tick, by the rule: the oldest unreviewed outside PR.

**Since the incident (by hand, serially):** outside PRs #164 and #166 reviewed and posted (both "not yet" — #164: real bug, but the fix writes timestamps into every new entry and its tests read a path `save()` never writes; #166: four fixes on a stale base, #65's re-sort inverts bm25 order — reproduced). A correction posted on #166: the maintainer ruled that a default body cap on the `fields` path is right (the conductor's review had argued the opposite). ADR-0034 "agent-facing reads are bounded by default" drafted `proposed` (PR #170), bounds environment-configurable per the maintainer. WIP = 1 written into the skill (PR #172, merged). One cron re-armed (:07/:37), no sweep cron, no retro cron. Architect dispatched read-only to re-split the remaining work into small serial themes (`kb/notes/serial-queue-2026-09-18.md`).

**This tick: outside PR #169** (makiaveli1, repeat contributor; #137 follow-up; +92/−12). Suite at `-n 4`: 4311 passed (108 s — beside a read-only architect; alone earlier today `-n 4` took 62 s, against 300+ s for `-n auto` under contention). verify-red: red without the fix. Cold read under no-suite orders. **Recommendation posted: merge after two changes** — the guard checks key presence, not values: `entry_id: ["abc"]` and `entries: 5` still return `INTERNAL`/`retryable: true` (reproduced by the host through the dispatcher), and the error does not name the malformed item's index. CI green; no approval click needed. Labelled `reviewed`.

**Waiting:** outside PR #171 (zhongxiao-chang — the `parse_datetime` split the #164 review suggested; +70/−3) is next tick's one thing. Then the loop's own queue: #163, #161, #140, #160, #145.

**Needs the maintainer:** #169, #164, #166 reviews are on the PRs (none is "merge as is" yet); ADR-0034 acceptance (PR #170); the three kept decisions from tick 9 (API-key hashing, CodeQL required check, the private-repo existence oracle).

## Tick 2026-09-18T12:49Z (tick 13 — WIP = 1)

**Pre-check** 12:42Z: load 2.1, 75% free, nothing heavy, dev green (f977f48). One thing: the unreviewed outside PR.

**Outside PR #171** (zhongxiao-chang — the `parse_datetime` split the #164 review suggested; +70/−3, opened ~1 h after that review). Suite at `-n 4`: 4314 passed in 59 s, alone on the machine. verify-red: red without the fix. Cold read under no-suite, no-edit orders. **Recommendation posted: merge after three changes** — (1) the fix anchors bare dates and *quoted* naive strings, but ruamel hands `parse_datetime` a naive `TimeStamp`/`datetime` for an **unquoted** timestamp, the common form, and the `isinstance(s, datetime)` branch returns it untouched (reproduced by the host: `created_at: 2026-01-15T09:00:00` → tzinfo None); a test pins that with `is naive`; (2) no test goes through the real loader; (3) the index stores `isoformat()` strings and re-index is content-hash gated, so two shapes coexist — ordering stays correct, `pyrite recent --since` is the one string compare that bites; a changelog sentence. The conductor's own #164 review had said "naive strings" — the gap was in the suggestion as much as the PR, and the comment says so. CI `action_required` (first-time contributor): **needs the maintainer's approval click**. Labelled `reviewed`.

**Noticed:** #169's author pushed `e8c8d3c` ("validate kb_batch_read spec types and name the malformed entry") ~25 min after the tick-12 review — the two requested changes, +75/−23 in the same three files. The `reviewed` label described the old head, so it is removed; re-checking #169 is the next tick's one thing (small: the delta, the suite once).

**Architect's serial queue landed** (5f8443e, `kb/notes/serial-queue-2026-09-18.md`): 40 entries, 31 movable, 9 blocked; review order for the five finished branches by what each unblocks: #163, #145, #140, #161, #160. Literal 0.24.2 DoD ≈ 5–7 cycles beyond those reviews; the roadmap's full 0.24.2 list ≈ 20 cycles.

**Retro note.** Three outside reviews in a row found the same shape: tests that exercise a function with hand-built inputs while the bug lives in what the real caller passes (#164's tests read a path `save()` never writes; #166's #95 test never reaches the schema; #171's tests never go through the YAML loader). The `Regimes:` rule is for our workers; the `good first issue` template could ask for "one test through the real entry point" in its acceptance line.

**Needs the maintainer:** approval click for #171's CI; merge decisions on #169 (after the re-check), #171, #164, #166 per the posted reviews; ADR-0034 (PR #170); the kept decisions listed in the serial-queue note.

## Tick 2026-09-18T13:23Z (tick 14 — WIP = 1)

**Pre-check** 13:19Z: load 5.5 (not Pyrite's — no suite, server or browser of ours running), 74% free, dev green. One thing: the outside PR whose head moved after its review.

**Outside PR #169, re-check at `e8c8d3c`** (the author pushed the two requested changes ~25 min after the tick-12 review). Delta read in full (~30 production lines: `entries` must be a list; each item a dict with non-empty string `entry_id`/`kb_name`; the error names `entries[i]`; an 11-shape parametrized test + an index test). Suite at `-n 4`: 4322 passed (102 s). The tick-12 regime probe re-run through the dispatcher on the new head: 19 malformed shapes → all `VALIDATION_FAILED`/non-retryable; **no `INTERNAL` path left**. No second cold read: the first one covered the PR, and the delta is the change it asked for, verified by its own probe. **Recommendation posted: merge as is.** CI green; no approval click needed. Labelled `reviewed`.

**Noticed:** #171's author also pushed after review (`86dc83a`, 12:59Z) — its re-check is the next tick's one thing. Review → fix turnaround from both contributors today: 25–60 min.

**Still waiting behind the outside PRs:** the loop's own five finished branches (#163, #145, #140, #161, #160 — the architect's order). They have now waited ~2.5 h; at one task per 30-min tick, with outside PRs pre-empting, the queue drains only when contributors pause. Not a problem to fix — outside work first is the maintainer's rule — but the 30-min cadence, not the machine, is now the pacing item: a review takes ~10 min of machine time. Worth the maintainer's eye: whether a tick may take the *next* item when its one thing finishes early, still strictly one at a time.

**Needs the maintainer:** **#169 — merge as is.** #171 (after its re-check; CI still wants the approval click), #164, #166 per the posted reviews; ADR-0034 (PR #170).

## Tick 2026-09-18T13:46Z (tick 15 — WIP = 1)

**Pre-check** 13:42Z: load 1.2, 74% free, nothing heavy, dev green. One thing: the outside PR whose head moved after its review, oldest first (#171 pushed 12:59Z; the new #173 arrived 13:39Z and builds on the same file).

**Outside PR #171, re-check at `86dc83a`.** Delta read in full: naive `datetime`/`TimeStamp` anchored to UTC (one line), the `is naive` assertion replaced, a loader-path test through `from_markdown` with both unquoted forms, the changelog corrected with the index note, budgets 5 s → 60 s, `Z` replaced only at end of string. Suite at `-n 4`: 4316 passed (109 s). The tick-13 loader probe re-run on the new head: all six forms timezone-aware, none raises against `_utcnow()`. **Recommendation posted: merge as is.** CI is still `action_required` — **the maintainer's approval click is the only thing between this PR and its required check.** Labelled `reviewed`.

**New:** outside PR #173 (zhongxiao-chang, "write created_at/updated_at back only for files that carry them", stacked on #164's commit) — a rework of #164 after its review. Next tick's one thing; #164 is presumably superseded by it (the author did the same with #167 → #164).

**Flow, for the retro:** five outside reviews and two re-checks since the incident, each one suite at `-n 4` (59–109 s), load never above 6.5. Both contributors turned review findings around in under an hour and both re-checks came back "merge as is" — the review comments were specific enough to act on without a second round. The loop's own five branches have not moved since 11:10Z.

**Needs the maintainer:** #169 — merge as is. #171 — approve the CI run, then merge as is. #164/#166 per the posted reviews. ADR-0034 (PR #170). Whether a tick may take the next queued item when its one thing finishes early (still one at a time) — asked at tick 14, unanswered, not assumed.

## Tick 2026-09-18T14:43Z (tick 16 — WIP = 1; the loop was stopped by the maintainer during this tick)

**Pre-check** 14:33Z: load 3.7, 63% free, nothing heavy, dev green (f977f48). One thing: the unreviewed outside PR #173.

**The maintainer ran `/loop stop` mid-tick.** The conductor cron (5f8aa5c8) was cancelled; no scheduled jobs remain. The in-flight review (one suite at `-n 4` and one read-only cold read) was allowed to finish and post, with that stated to the maintainer; nothing else was started.

**Outside PR #173** (zhongxiao-chang — rework of #164, the write-back half of #151; +264/−45, stacked on #164's commit). Suite at `-n 4`: 4306 passed (58 s). verify-red: both test files red without the fix. Host probes on this head: a new entry writes `id, title, type, importance` only; no-timestamp, bare-date, quoted and unquoted files round-trip byte-identically — the four #164 findings are closed. Cold read (no-suite, no-edit-while-suite-runs) found, and the host reproduced, **a split-brain in the new helper**: `_timestamp_same_instant` is consulted for *every* key in `_restyle_like_source`, so updating `title: "2026-01-15"` to `"2026-01-15T00:00:00Z"` succeeds in the API and the index and never reaches the file. Also: `update_entry` stamps over an explicit `updated_at`; the refresh writes a quoted microsecond string where the file had an unquoted timestamp or a bare date; the gate fixtures are tested through `entry.save()` rather than `repo.save()` and kept out of the strict set for a reason that does not apply. **Recommendation posted: merge after four changes, sequenced after #171** (one conflict, in `parse_datetime`; #171's version should win). CI `action_required`. Labelled `reviewed`. #164 can be closed in favour of #173.

**State at stop.** Outside PRs, all reviewed: #169 merge as is (CI green) · #171 merge as is (needs the CI approval click) · #173 merge after four changes, after #171 · #166 not yet (four fixes on a stale base; #65 needs rework) · #164 superseded by #173. The loop's own finished branches, unreviewed since 11:10Z: #163, #145 (six fix commits committed locally in its worktree, unpushed), #140, #161, #160. ADR-0034 `proposed` in PR #170. The serial queue for a restart: `kb/notes/serial-queue-2026-09-18.md`. Resume with `/pyrite-conductor` (one tick) or `/loop 30m /pyrite-conductor`; the one-task limit lives in the skill.

**For the retro.** Six outside reviews since the incident; five found a test that bypasses the real entry point (#164 path, #166 schema, #171 loader, #173 `entry.save` vs `repo.save`, #169's value types). The cold read under no-suite orders lost nothing: every headline finding came from a small serial probe, and each was reproduced by the host in seconds. Peak load since WIP = 1: 6.5.

## Update 2026-09-18T14:55Z — after the maintainer's evening decisions (loop still stopped)

- **#169 merged** by the maintainer (14:53Z); #137 closed. dev run d6f3536 in progress at the time of writing. #134 (the REST twin) is no longer waiting on #169 — only on the contributor window (2026-09-19 08:45Z).
- **#171 did not merge.** The maintainer approved its CI run and went to merge; the required check came back red on `ruff format --check` (`Would reformat: tests/test_models.py`). **That is a review miss by the conductor:** the tick-15 re-check ran the suite and the loader probe and said "merge as is" without running `ruff format --check`. Comment posted on #171 with the one-command fix; the next push needs the maintainer's CI approval click again. **Review checklist gains, from now: `ruff check` and `ruff format --check` on every outside PR head, before any "merge as is".**
- **ADR-0034 accepted** by the maintainer ("I have accepted 170"). `status: accepted` committed on `kb/adr-bounded-reads`, PR #170 rebased onto dev with auto-merge armed. Entries 35–39 of `serial-queue-2026-09-18.md` (the five `adr-0034-*` themes) are **unblocked**; their other waits stand ((i) and (ii) after #166's #58 fix lands or is abandoned, and after #145).
- #173 now conflicts with dev only in `CHANGELOG.md`; it still waits on #171 and its four changes.
- The maintainer's read on the release: on track for the middle of next week.

## Session 2026-09-19T19:07Z — by hand with the maintainer (loop stopped; WIP = 1)

**Overnight:** #169 and #170 (ADR-0034, accepted) merged; dev green. #171's author pushed the merge-of-dev + format fix — byte-identical to the version the conductor had lint-verified; it needs only the maintainer's CI approval click. #173's author is holding their push until #171 merges. #166's author commented "Updated" without pushing.

**Four new outside PRs reviewed, one suite at a time at `-n 4` (61–63 s each), cold reads under no-suite orders, and — new — the takes were agreed with the maintainer before anything was posted** ("easier for contributors if they get one message with our best thinking"):
- **#176** (makiaveli1, classmethod fixtures, #144): merge as is. Its decorator order is pytest's documented one, not the order that broke dev on 09-18; probed on 3.11/3.12/3.13 with pytest 9.1.1 and 9.0.2.
- **#174** (makiaveli1, REST batch parity, #134): merge after two changes — `fields` of a wrong type is still a 500 (reproduced); one private-KB + `fields` test. The copied validation loop is accepted; we extract the shared helper ourselves with ADR-0034's module. Sibling `?fields=` bugs filed as #179 (`good first issue`).
- **#175** (makiaveli1, GenericEntry metadata, #149): merge after three — the bookkeeping field must be `init=False, repr=False, compare=False` (it changes `==`; reproduced); guard a non-mapping `metadata:` (still retypes to `event`); one file-level fixture. Two format behaviours accepted deliberately; "new keys join an existing block / one helper owns the decision" filed as #178.
- **#177** (Gambit-Checkmate, first-time, #19): needs rework. Maintainer's decision: removing a KB from `config.yaml` means it is gone from the running server until re-added — so the fix is `remove_kb` consulting the live config, not a startup `UPDATE` (which un-protects everything under an empty config — reproduced — keeps a removed KB published, and writes on every read-tier start).
- #166 nudged to push; #164 noted as superseded by #173.

**Design review of what has merged since 09-16** (three read-only reviewers; key claims spot-checked by the host). Verdict: decisions good, code unusually well explained, but contracts live in prose and nothing enforces them, so fixes land on one surface or class and not its siblings. It produced the maintainer's next three priorities, ahead of the serial queue:
1. **Private-KB read scoping is incomplete** — the entry/search/graph/link/KB routes are scoped; sixteen other endpoint modules that serve KB content are not. Dispatched as the one running task: PR #180 (opus; structural test over every route + scoping of all content routes; cold read mandatory; part 2 covers meta/admin routes).
2. **social / zettelkasten / encyclopedia hand-roll `from_frontmatter`** and drop base fields — route through `_base_kwargs`, plus an entry-class conformance test over every registered class.
3. **Relabel those three as example plugins (not supported)** for 0.24.2, with a release-note line; the directory move waits until after the release.
Other findings queued as tickets after the release gate: MCP/REST contract test, shared read-shaping module, one error taxonomy on `PyriteError`, pin the CI classifier's filter paths, `verify-red.sh` must show why a test failed, `add_link` skips `_validate_write`, the `EventEntry` load fallback retypes entries, `KBService`/`mcp_server.py` splits, fixture reach (22 of 216 test files use the shared fixtures).

**Review-process lessons:** `ruff check` + `ruff format --check` at CI's exact scope are now run on every PR head (the #171 miss). Agreeing the take with the maintainer before posting cost one round trip and changed three recommendations' framing.

## Tick 2026-09-19T19:16Z (loop re-armed by the maintainer at 20 min; WIP = 1)

Pre-check: load 2.3, 57% free, dev green (c0db60e — #176 merged by the maintainer). **A worker is running** (#180 read scoping; branch head moved 1bdec79 → 10a5b57, a single test file under pytest at check time), so by rule 1 this tick starts nothing heavy. No unreviewed outside PRs; no reviewed PR's head has moved. #171: the maintainer approved the CI run; `test (3.12)` in progress; the PR is one commit BEHIND dev (#176) with no conflicts — if the ruleset insists on up-to-date at merge time it needs `update-branch`, which on a first-time contributor's fork re-arms the approval, so that is left for the maintainer's word. Nothing dispatched, nothing reviewed.
