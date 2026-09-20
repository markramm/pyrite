---
id: adr-0033
type: adr
title: "Where work is tracked: GitHub issues for bugs and requests, the KB for the roadmap"
adr_number: 33
status: accepted
deciders: ["markr"]
date: "2026-09-17"
tags: [process, backlog, github, contributor-experience, governance]
links:
- target: adr-0032
  relation: related
  kb: pyrite
- target: adr-0019
  relation: related
  kb: pyrite
- target: contributor-docs-pass-contributing-security-pr-template-credits
  relation: related
  kb: pyrite
---

# ADR-0033: Where work is tracked

## Context

Everything — bugs, feature ideas, tech debt, epics, design work — currently lives
in `kb/backlog/` as markdown, queried with `pyrite sw backlog`. That was the right
call when the only people filing work were the maintainer and his agents, and it
is good dogfooding. Three things have changed:

- **Pyrite has users and an outside contributor, and they cannot reach the
  backlog.** Filing in `kb/backlog/` means cloning the repo, learning the
  frontmatter, and opening a PR. The contributor opened GitHub issues #1 and #2
  instead, which is what anyone would do. The 2026-09-17 review found zero open
  GitHub issues, an unused `good first issue` label, and a CONTRIBUTING that says
  "check existing issues".
- **ADR-0032 makes a KB ticket cost a pull request and a CI run.** That price is
  right for a considered roadmap item and wrong for "this command crashed when I
  did X" — capture has to be cheaper than the thing being captured.
- **The backlog no longer reads as a plan.** 119 open items: 38 features, 34
  improvements, 17 bugs, 8 tech-debt, and a tail. A reader cannot tell what the
  project intends to build from what happened to break last Tuesday.

## Decision

### 1. Two places, split by who files and what it costs

| | GitHub Issues | The KB (`kb/`) |
|---|---|---|
| **Holds** | Bug reports; feature requests and feedback from users | The roadmap: epics, backlog items (planned work), ADRs, designs, standards |
| **Filed by** | Anyone — users, contributors, the maintainer, agents (`gh issue create`) | The maintainer and agents, through a PR (ADR-0032) |
| **Cost to file** | Seconds, no clone | A PR and a CI run (about a minute on the KB-only fast path) |
| **Answers** | "What is broken? What are people asking for?" | "What are we building, in what order, and why?" |

### 2. One item, one home; the other side links

Two trackers fail the same way every time: the same item in both, drifting, until
neither is trusted. So:

- **A bug lives in GitHub, only.** The fixing PR says `Fixes #N`. It never gets a
  mirror ticket in the KB.
- **A bug whose fix needs a design decision** gets an ADR or a backlog item *for
  the design*, which links the issue. The issue is still where the bug is
  tracked and closed.
- **A feature request the maintainer accepts** becomes a backlog item carrying
  `github_issue: N`. The issue gets the `roadmap` label and stays open until the
  work ships, so the person who asked is told. The backlog item is the source of
  truth for scope and sequencing; the issue is the conversation with the
  requester.
- **A request that is declined** is closed with the reason. Governance is BDFL
  (ADR-0032): the maintainer decides what enters the roadmap.
- **Work the maintainer or an agent originates** — a feature, an improvement,
  tech debt, a refactor — goes straight to the KB. It does not need an issue.
- **A bug an agent finds** goes to GitHub like anyone else's, under the same
  rule that governs the public KB: placeholders for private subjects and paths.
- **Security reports never go in public issues.** They use GitHub private
  vulnerability reporting, which must be enabled for SECURITY.md to be true.

### 3. What the backlog becomes

`kb/backlog/` is the feature roadmap: `kind` is one of `feature`, `improvement`,
`tech_debt`, `refactor`, `epic`. `kind: bug` stops being created there. A roadmap
item should be something a reader could see on a "what's coming" page without
surprise. `pyrite sw backlog`, the kanban flow, the epics and the ADR links all
continue unchanged — this is the part of the dogfooding worth keeping.

### 4. GitHub setup

- Issue templates: **Bug report** (version, install path, steps, expected/actual,
  logs) and **Feature request / feedback** (the problem first, then the idea).
  A `config.yml` that routes security reports to private reporting and questions
  to Discussions if enabled.
- Labels beyond the defaults: `roadmap` (accepted; linked from a backlog item),
  `needs-design` (blocked on an ADR or design), `needs-repro`, plus area labels
  that match the code map (`cli`, `server`, `mcp`, `web`, `extensions`, `docs`).
  `good first issue` gets used: 5–10 starter items at all times.
- A response-time intent, written in CONTRIBUTING: acknowledged within a week.
  The three outside PRs waited 7–8 days with one comment between them.

## Consequences

**Easier**
- Users and contributors have an obvious, zero-setup place to report and ask.
- Bug capture is free, so more of it happens — including by agents mid-task, who
  today skip filing because it costs a commit.
- The backlog reads as a plan again, and can be published as one.
- `Fixes #N` closes the loop automatically; release notes can be generated from
  closed issues and merged PRs.

**Harder**
- **Agents lose bugs from `pyrite search`.** KB search is how a session gets
  context, and GitHub issues are not in it. Until that is addressed an agent
  starting work in an area must also run `gh issue list --label <area>`; the
  pyrite-dev skill's "before writing code" checklist gains that line. The real
  fix is on-pitch for the product — a read-only importer that syncs a repo's
  issues into a KB (`type: github_issue`) so they are searchable and linkable
  like anything else — and is filed as a roadmap item, not built now.
- **Part of the dogfooding goes.** Bug triage leaves the software-kb kanban. The
  roadmap, epics, ADRs and review flow remain, which is where the tool is
  distinctive; bug tracking is not where Pyrite needs to compete with GitHub.
- **Two places to look** for "what is open". Mitigated by rule 2 (no item is in
  both) and by the `github_issue` link on every accepted request.
- **The issue tracker is public and unmoderated by schema.** Private material
  that the KB's conventions kept out can arrive in an issue body. Agents filing
  issues follow the placeholder rule; the maintainer edits or deletes as needed.

## Migration (after v0.24.1)

1. Enable private vulnerability reporting; add the templates, labels and
   `config.yml`.
2. Move the open `kind: bug` items. Proposed split of the 17 open today:
   - **To GitHub issues** (a user can hit them): `web-search-results-never-render`,
     `web-kb-context-single-authority`, `web-fix-dropped-kb-seams`,
     `web-light-mode-chrome-repair`,
     `first-write-on-a-fresh-install-blocks-...-embedding-model`,
     `writes-accept-off-enum-field-values-...`,
     `core-types-silently-drop-unknown-frontmatter-keys`,
     `entry-ids-from-non-ascii-or-very-long-titles-...`,
     `sw-new-adr-does-not-slugify-punctuation-...`,
     `index-health-exit-non-zero-when-unhealthy-...`,
     `kb-remove-permanently-refuses-a-kb-...`,
     `railway-one-click-deploy-likely-fails-...`,
     `db-backup-writes-into-the-current-directory-...`,
     `fts-search-result-fragmentation` (deferred → open with `needs-design`).
   - **Stay in the KB, re-kinded** (internal process work, not user-facing bugs):
     `tests-must-not-inherit-git-env-autouse-fixture` → `tech_debt`,
     `single-source-of-truth-for-the-version-asserted-by-a-test` → `improvement`,
     `scrub-private-material-and-machine-paths-from-tracked-files` → `task`.
   Each migrated file moves to `kb/backlog/done/` with `status: superseded` and a
   `github_issue: N` field, so links into it keep resolving and the history stays.
   *Do not run `pyrite update` on them until
   `core-types-silently-drop-unknown-frontmatter-keys` is fixed — it strips
   undeclared keys such as `milestone`.*
3. Seed 5–10 `good first issue` items from the small, well-specified ones above.
4. Update CONTRIBUTING, the PR template (`Fixes #N`), the pyrite-dev skill
   (where to file what; the `gh issue list` step) and `kb/backlog/README.md`.
5. ~~File the roadmap item for the GitHub-issues importer.~~ Decided 2026-09-17:
   not a priority. The pyrite-dev skill checks GitHub with `gh` when working on
   the roadmap or toward a release; the importer stays in "later, unscheduled".

## Decisions (2026-09-17, markr)

Steps 1–3 of the migration ran the same day: labels, issues #9–#21, files
superseded. The importer is not a priority; agents use `gh` directly.

## Open questions

1. **GitHub Discussions for questions and open-ended feedback?** Leaning yes once
   there is enough traffic to need it; until then a `question` label is enough.
2. **Do internally found bugs always go to GitHub, even trivial ones fixed in the
   same session?** Proposed: no issue needed when the fix lands in the same PR
   that found it; the PR description is the record.
3. **Should `github_issue` become a declared field on `backlog_item`** in the
   software-kb plugin (so it survives `pyrite update` and can be queried)?
   Proposed: yes, as part of step 2.

## Amendment 2026-09-20 (accepted) — process findings live in the KB

**Decision (drafted by the conductor on the maintainer's instruction, 2026-09-20: "keep those in the pyrite kb rather than in github"):** findings about *how the loop works* — a skill that did not say, a script that assumed, a check that fired late, a review that could not see something — are recorded as backlog items in `kb/backlog/` tagged `process`, not as GitHub issues. GitHub keeps what it had: bugs and requests from users and contributors, and the tasks the maintainer assigns to themself (the org move, #182). The roadmap stays in `kb/`.

**Why:** on 2026-09-20 the `process` label held 16 open issues; a groom pass found 11 of them already fixed by merged skill changes and nobody had closed them, because the fix lived in a skill file and the record lived in another tracker. A process finding is a fact about this repository's own practice — the skills, the scripts, the ADRs — and belongs beside them, where `pyrite search` finds it, the retro reads it, and the fix's PR can close it by moving the item to `done/` in the same commit. It also keeps the public issue list to what an outside contributor can act on.

**How it applies:** the conductor and its workers file friction with `pyrite create -k pyrite -t backlog_item --tags process` on the log branch (or the theme branch when the fix is in the same PR); the retro (`pyrite-meta-conductor`) reads `pyrite sw backlog` filtered on `process` instead of `gh issue list --label process`; the five items open on the day of the amendment (#189, #133, #122, #115, #103) were migrated with their triage text and the GitHub issues closed pointing at the item ids. The `process` GitHub label stays for anything an outside contributor files that turns out to be about practice; the conductor migrates it.

**Status:** accepted by the maintainer on 2026-09-20 (ADR-0032).
