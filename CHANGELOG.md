# Changelog

All notable changes to Pyrite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Unreleased changes are **not** listed below. Each one is a separate file under
[`changelog.d/`](changelog.d/README.md), named `<slug>.<section>.md`, so that no
two pull requests conflict on this file; `scripts/release.py` assembles them
under the version heading when the release is cut. `tests/test_changelog_fragments.py`
asserts that `[Unreleased]` stays empty.

## [Unreleased]

## [0.24.3] - 2026-09-20

"Operational" — see `kb/roadmap.md`.

**The last release from `markramm/pyrite`.** The repository moves to the
`pyrite-wiki` organization next, and 0.25 will be the first release from its
new home. Eight of the 86 pull requests merged into this release came from
outside contributors — @Voyagerroc-Lab, @YaoSong808, @fathirramadhan-web,
@makiaveli1 and @zhongxiao-chang. That is 9%. Of the pull requests open as
this release was cut, 11 of 13 are theirs.

The move is not a rename. It is what makes pull request queues, contributor
permissions and a home for community extensions possible — and the point at
which Pyrite stops being one person's experiment.

### Fixed

- The `pyrite` CLI now configures the package logger at startup, so warnings
  use the standard timestamped stderr format without tracebacks while JSON
  stdout remains parseable. Library imports install only a `NullHandler` and
  leave application and root logging configuration untouched (#196).

### Security

- **Private-KB content was readable over MCP-over-HTTP by any logged-in
  user.** The `/mcp` mount resolved a global tier from the caller's
  credential and applied no per-KB read scoping anywhere in its path — the
  one KB-content surface the REST-side fix did not reach. A plain read-tier
  user could read entry **bodies** from a KB they had no grant on: `kb_get`,
  `kb_read_body`, `kb_list_entries` and `kb_search` all served it, and
  `kb_list` named the KB. MCP now resolves the caller's readable set per
  connection, through the same helper the REST routes use, and enforces it
  at all three content chokepoints: tool dispatch, resources and prompts. A
  KB the caller may not read is reported exactly as one that does not exist,
  so its existence stays private. Anonymous callers were never exposed —
  `/mcp` already rejected them. Operator API keys, global admins and local
  stdio are unscoped, unchanged. Tools that span every KB and cannot yet
  filter (45 extension tools taking an *optional* `kb_name`) are refused for
  a scoped caller rather than served across the whole index; naming a
  readable KB makes them work as before.
  ([#201](https://github.com/markramm/pyrite/issues/201))

- **`web/` dependency bump closes 16 of 19 open Dependabot alerts.** `vite`
  7.3.1 → 7.3.6 (range pinned to `^6.0.0 || ^7.3.5` so it cannot resolve
  below the patched line; GHSA-4w7w-66w2-5vf9, GHSA-v2wj-q39q-566r,
  GHSA-p9ff-h696-f583, GHSA-v6wh-96g9-6wx3, GHSA-fx2h-pf6j-xcff), `svelte`
  5.53.3 → 5.57.0 (direct bump; six SSR/XSS/ReDoS advisories, patched at
  5.53.5 and 5.55.7), `postcss` 8.5.6 → 8.5.28, `picomatch` 4.0.3 → 4.0.7,
  `esbuild` 0.27.3 → 0.28.2 (all three transitive, via `npm update`, no
  direct pin or override needed). `cookie` (GHSA-pxg6-pf52-xh8x) stays open:
  it is pinned to `^0.6.0` by `@sveltejs/kit` 2.x, and the fix needs
  `cookie` ≥0.7.0, which only a breaking `@sveltejs/kit`
  3.x/`adapter-node`/`adapter-static` major would allow.

- CI workflow jobs now declare least-privilege `permissions:` explicitly
  (workflow-level `contents: read`, plus `pull-requests: read` on the
  `changes` job for `dorny/paths-filter`) instead of running with the
  repository's default `GITHUB_TOKEN` scope. Closes the eight CodeQL
  `actions/missing-workflow-permissions` alerts on `ci.yml`.
- **Repo endpoints returned raw git stderr in their *error* bodies, disclosing
  the server's absolute filesystem paths to any write-tier caller.** `POST
  /api/repos/subscribe` on a missing repo answered `400 {"message": "Clone
  failed: Cloning into '/Users/<user>/.pyrite/repos/…'…"}`; `/api/repos/fork`
  and `/api/repos/{name}/pr` had the same shape, and `/api/repos/{name}/sync`
  nested the same text in a 200 body. Every such message is now redacted —
  absolute paths (including ones containing spaces, `~` and Windows drive
  paths) replaced with `<path>`, tokens with `***` — while the full stderr is
  logged at WARNING so the operator loses nothing (CodeQL
  `py/stack-trace-exposure` #51, #52, #53). Clone failures are additionally
  classified into stable, documented codes (`REPO_NOT_FOUND`, `AUTH_REQUIRED`,
  `BRANCH_NOT_FOUND`, `PATH_EXISTS`, `CLONE_TIMEOUT`, `INVALID_REQUEST`,
  falling back to `CLONE_FAILED`); see `docs/json-contracts.md`. Pull and push
  keep returning git's own words, redacted — a merge conflict or a rejected
  push still says so, and remote URLs the caller supplied are preserved.
  Success bodies (`RepoInfo.local_path`, `subscribe`'s `path`) narrowed to
  the workspace-relative form in the entry below.
- **Repo endpoint *success* bodies disclosed the same absolute server paths
  #161 removed from error bodies.** `RepoInfo.local_path` (`GET /repos`, `GET
  /repos/{name}`) and the `path` key in `subscribe`/`fork` responses returned
  the server's real filesystem path (`/Users/<user>/.pyrite/repos/owner/repo`)
  at 200. Both are now relative to the workspace root (`owner/repo_name`) —
  the field stays populated rather than dropped, since `RepoInfo` is public
  REST response shape an external consumer may already read, but discloses
  no server layout or usernames; a path outside the workspace root comes back
  as `"<path>"` rather than leaking the absolute value or raising. Only the
  HTTP boundary changed — the CLI (`pyrite repo list`/`status`) still shows
  the real absolute path for the local operator, and every internal caller
  (fork's `add_remote`, sync, PR, config load) still reads `local_path`
  absolute off the DB row or the service's own dict, unaffected. See
  `docs/json-contracts.md`.
- **Private KBs were readable by any logged-in user, and by anonymous
  visitors on an auth-enabled instance.** Per-KB roles (`default_role: none`,
  explicit grants) were enforced on write routes only; every read route
  returned private content, and search and the KB list disclosed it. Read
  routes now require read on the named KB (404, so a private KB's existence is
  not disclosed either) and cross-KB routes are filtered to the KBs the caller
  may read, in SQL for list, count and keyword search. Operator API keys are
  unaffected (they are the operator's credential). MCP is operator-level and
  unchanged.

  Every route serving KB content is now covered. The first pass reached
  entry by id, list, search, batch read, graph, export and KB
  info/schema/orient; a second pass reached the sixteen endpoint modules
  it had missed — `/tags` and `/tags/tree` (a tag name and its count
  disclose a KB), `/timeline`, `/qa/status`, `/qa/validate`,
  `/qa/validate/{entry_id}`, `/qa/coverage`, both `/entries/{id}/versions`
  routes, `/entries/{id}/blocks`, `/daily/dates` and `/daily/{date}`, all
  four `/collections` reads, `/tasks`, `/starred`, the three
  `/kbs/{kb}/templates*` routes, the three `/reviews` reads, and the four
  `/ai/*` POSTs, whose retrieval now only sees readable KBs. Where a
  route spans KBs the filter is pushed into the query, so `count`,
  `total` and `limit` are computed over readable rows only — a count of
  three for a KB you cannot read is itself a disclosure.

  **A request that names a knowledge base in more than one place is now
  checked against every one of them.** A request can name a KB in its path,
  in either of two query spellings (`kb`, `kb_name`) and in its JSON body,
  and the permission check used to stop at the first place it looked while
  the handler read a different one — so pairing a knowledge base you may
  read with one you may not could return the second one's content, or
  authorise a write to it. Every KB a request names must now be permitted:
  readable for a read route, and at the required tier for a write route.
  A request whose body cannot be parsed is refused rather than treated as
  naming no KB at all.

  `GET /api/kbs/{kb}/changes`, which returns uncommitted entry-level diffs,
  now requires read access to that KB as well as the global read tier.

  `tests/test_read_scoping_is_structural.py` now enforces this: it walks
  the real app's routes and fails for any `/api` route that declares no
  read-scoping dependency and is not on an explicit allowlist where every
  entry carries a reason — and, since a declared check is not the same as a
  check that looked in the right place, it also fails any scoped route that
  reads its KB from somewhere the resolver does not inspect. A new unscoped
  route fails CI with instructions. Meta and admin surfaces (`/stats`,
  `/plugins*`, `/settings*`, `/repos*`, `/worktree*`, the remaining git-ops
  routes, MCP over HTTP) are allowlisted pending the same treatment; they
  are tier-guarded today but not per-KB scoped.

### Fixed

- REST field projections now preserve `id` and `kb_name` (Berkay Byte).

### Added

- **`pyrite --version` (also `-V`), which had never existed.** The CLI
  answered `Error: No such option: --version` for every release up to this
  one. The version itself was never wrong — `pyrite.__version__` reads from
  `pyproject.toml` with an installed-metadata fallback, and a test has pinned
  it since it drifted to `0.12.0` while `pyproject.toml` said `0.24.1`. That
  test covered the package attribute; nothing covered the command line, which
  is the surface a user meets first. Found by the release script's own
  release-layer step on its first real run, against a clean install from the
  release SHA.

- **`scripts/release.py`: a release is one command.** Six ordered steps, with
  every check in front of the first thing that cannot be undone —
  preconditions (clean `dev` at `origin/dev`; `origin` really being the repo
  the `gh` calls name; `vX.Y.Z` existing neither locally, on `origin`, nor as
  a GitHub release, and `origin/main` already an ancestor of the SHA, so the
  publish can only ever fast-forward; the version; a dated CHANGELOG section
  with content; the `release-blocker` label existing, with no open PR carrying
  it), the required CI checks green on that exact SHA (newest run per check
  name, so a rerun to green counts; `--wait-ci` waits, 15 minutes by default),
  the release layer verified *before* the tag exists (install from the SHA
  into a throwaway venv, `pyrite --version`, the getting-started tutorial run
  against that install, a Docker build when docker is present), then `main`,
  the tag and the GitHub release, then reopening `[Unreleased]` on its own
  branch for a PR to `dev`, then a handoff step naming what the release cannot
  do. `--dry-run` is the default and prints every command, writing nothing to
  disk; `--execute` is the only way anything is written. It never passes
  `--no-verify`, never force-pushes, never deletes a ref and never creates a
  label. A failure after the publish step began lists which commands already
  ran rather than claiming nothing was attempted.
  `scripts/run_tutorial.sh` gains `PYRITE_TUTORIAL_VENV` so the tutorial can
  be run against an arbitrary install rather than the checkout's.
- Repo-local configuration: a `.pyrite/config.yaml` in the current directory
  or any parent is used instead of `~/.pyrite` when no `PYRITE_CONFIG_DIR` /
  `PYRITE_DATA_DIR` is set, so a checkout (or a git worktree) can carry its own
  KB registry and index. `scripts/new-worktree.sh` creates one per worktree.
- **A smoke layer: every interface has an end-to-end test in CI.** `tests/e2e/`
  starts `pyrite-server` as a subprocess on a free port against a temp data
  dir and drives it the way a user's client does — REST (`POST /api/kbs`, then
  `POST /api/entries` into it with no restart, then `GET /api/search`), MCP
  over SSE (the advertised `event: endpoint` path, then initialize, tools/list
  and a `kb_search` call over that session), MCP over stdio (`pyrite mcp
  --tier read` as a subprocess speaking JSON-RPC, its tool list asserted equal
  to the SSE one), and embedding prewarm read from `/health` with no write
  issued. `scripts/run_tutorial.sh` runs `docs/getting-started.md` as a test:
  its bash blocks, in order, in one shell session in a temp HOME, against the
  installed package. Each of the three bugs an outside contributor found
  (PRs #3, #4, #5), reintroduced by hand, fails one of these tests while the
  existing 3316 pass. Marked `e2e` and excluded from the default run, so pull
  requests stay at ~3 minutes; a new `smoke` CI job runs it on the push to
  `dev` and on manual dispatch, and is deliberately not a required check
  (ADR-0032 §3a's breadth row).
- `auto_embed` setting (`PYRITE_AUTO_EMBED=0` to disable): embed entries on
  write, on by default. Off means keyword search only, no torch import and no
  model download on the write path; `pyrite index embed` backfills later. The
  first half of #13 (first write on a fresh install blocked on the download).
- `PyriteDB` is a context manager: `with PyriteDB(path) as db:` closes the
  connection on block exit (and on an exception), so callers no longer have to
  remember a manual `db.close()`.
- **The round-trip identity gate.** `tests/test_roundtrip_identity.py` loads
  every entry in a temp copy of the real `kb/` (774 files) through
  `KBRepository`, saves each back untouched, and asserts the bytes are
  byte-identical — the class of bug behind #46, #86 and #87 ("save wrote
  something load did not read") now fails the default suite instead of
  waiting for a human to notice a huge diff in review. Runs in ~1-2s.
  `tests/fixtures/roundtrip/` adds hand-built adversarial shapes (inline vs
  block lists, quoted scalars, a markdown table with `---` dividers, YAML
  anchors/merge keys, a missing trailing newline). 70 real-corpus ids are
  `xfail(strict=True)`, individually and by name, across five classified
  causes: 46 bare-string `links:` items (the residual #69 left, deferred —
  see the fix's own design notes), 11 block-indented `links:` sequences and
  1 `GenericEntry` metadata-duplication case (new findings, filed as #148 and
  #149), 6 files with pre-existing #87 `body:`-fold corruption already
  committed to `kb/` (#150, a data-cleanup issue, not a code bug), and 6
  daily notes normalized by `to_markdown`'s one-trailing-newline rule (not a
  bug). A sixth finding, `created_at`/`updated_at` silently dropped on save
  (issue #151), is pinned by two fixtures rather than a corpus id, since no
  real file uses those keys yet.

### Process

- CI parity: the `ruff check` / `ruff format --check` step now covers
  `extensions/` (54 pre-existing findings fixed: import sorting, unused
  imports/variables, a loop variable, two UP rules), matching the commit-stage
  hook that already lints it — a PR could otherwise go green with lint debt a
  local commit would have blocked. A new `pull_request`-only CI step runs
  `check_fix_commit_has_tests.py --range` over the PR's own commit range, so a
  `fix:` commit without a `tests/` change fails CI even for contributors who
  never ran the local commit-msg hook (all three outside PRs so far were
  fixes without tests). `tests/test_dev_process_config.py` pins both.
- The weekly retrospective: `pyrite-meta-conductor` now says what worked,
  root-causes every failure in its window and fixes what it finds as one
  process change plus one `quality` theme (refactoring, test refactoring) the
  conductor dispatches ahead of features once a week. The conductor leaves a
  tick log in `kb/notes/conductor-log-<week>.md`, files process friction as
  `process` issues as it happens, and stops at the release plan.
- Three skills replace one: `pyrite-dev` is the worker (one theme, one branch,
  one worktree, TDD, a report), `pyrite-conductor` picks work from GitHub
  issues and the roadmap, composes reviewable themes, dispatches a
  `pyrite-worker` agent per theme (Sonnet 5 or Opus 5 by shape of work),
  reviews branches with a `pyrite-reviewer` cold read for risky changes, opens
  and shepherds PRs, and keeps the repo healthy; `pyrite-meta-conductor`
  watches the conductor's loops for the constraint and proposes one measured
  change per run. A PR is one complete theme.
- ADR-0032 is in force: work happens on feature branches, each in its own
  worktree (`scripts/new-worktree.sh <branch>` sets one up with venv and
  hooks); `dev` takes pull requests only, checks green on top of current
  `dev`, no bypass; `main` fast-forwards to CI-verified commits; `v*` tags are
  immutable. Rebase is the default merge. ADR-0033: bugs and requests live in
  GitHub issues, the roadmap in `kb/`.
- The test runner is pinned exactly (`pytest==9.1.1`, `pytest-cov==7.1.0`,
  `pytest-xdist==3.8.0` in the `dev` extra), so every worktree venv and every
  CI leg run the identical version — an unbounded `pytest>=8.0.0` had
  resolved 9.1.1 on 3.12 and 9.0.2 on 3.13, and #81's fixtures passed the
  one-interpreter PR gate under 9.1.1 and broke `dev` on 3.13 under 9.0.2.
  `tests/test_dev_process_config.py` asserts the pins stay `==`. Ruff's `PT`
  (flake8-pytest-style) rule set is now enabled for `tests/` and fixed 14
  mechanical findings (fixture-parentheses, useless-yield, parametrize-tuple);
  the four remaining rule codes need per-call-site judgment and are ignored
  with reasons in `pyproject.toml`. Refresh a worktree venv after this with
  `uv pip install --python .venv/bin/python -e ".[all,dev]"`.

### Documentation

- Six false statements in agent-facing docs, found by a cold read and
  independently re-verified (#229): `CLAUDE.md` documented a `--title` flag
  `pyrite sw new-adr` does not have (title is positional; same fix applied
  to `.claude/skills/kb/SKILL.md` and `.claude/skills/software-kb/SKILL.md`,
  which repeated it) — **@Umar-2026 found and fixed the same `--title` bug
  independently in #237, fourteen minutes before this sweep merged**;
  `docs/json-contracts.md`'s `has_more`/`total` claims
  are replaced with a measured per-surface, per-transport table (`search`,
  `list_entries`, `recent`, `tags`, `backlinks` × CLI/MCP/REST — none of
  them uniform); the 29/11/8 MCP tool-tier counts in `docs/getting-started.md`,
  `README.md` and `pyrite mcp --help` undercounted by 2.4x by omitting 41+
  plugin tools exposed per tier — `pyrite mcp --help`'s counts are now
  generated from the live tool registry (true counts: read 70, write 103,
  admin 112) and the other two docs point to it instead of retyping a
  number; `docs/gemini-mcp-integration.md` and `docs/openai-mcp-integration.md`
  now name which binary (`pyrite mcp` vs `pyrite-server`) each tier default
  applies to, since the two disagree (`write` vs `read`); `kb_bulk_create`'s
  MCP tool description no longer claims best-effort per-entry semantics
  (#95: one malformed entry rejects the whole batch); `AGENTS.md` now says
  `pyrite orient`'s schema block has no field list for plugin-declared
  types (#232) instead of implying it always does.
- `kb/runbooks/setting-up-dev-environment.md` (#212): the troubleshooting
  runbook had drifted from CONTRIBUTING and could not run the suite —
  `pip install -e ".[dev]"` (no `fastapi`, no CLI deps, cannot collect
  tests) is now `.[all]`; the extension install is a `for ext in
  extensions/*/` loop instead of an enumerated list missing `cascade` and
  `journalism-investigation` and naming a nonexistent `task` extension; the
  hard-coded "1780+ tests" is replaced with the `--collect-only` command
  itself, per the counts-drift backlog item.
- CONTRIBUTING: the AI-assisted-contribution note now accepts a git
  `Co-authored-by:` trailer as the declaration (machine-readable, survives
  squash-merge) alongside the existing, still-welcome PR-body mention.
- CONTRIBUTING rewritten for a project with contributors: branch flow and
  required checks (ADR-0032), the three hook stages, where bugs vs roadmap
  items live (ADR-0033), a one-week first-response intent, how to run the
  suite. PR template asks for `Fixes #N` and the failing test; issue templates
  ask for version and install path and route security reports privately.
- README: plugin protocol method names corrected (`get_entry_types`,
  `get_cli_commands`, `get_hooks` incl. `before_index`), eleven built-in types,
  `pyrite/schema/` package, extension list, test and ADR counts, the install
  section shows the git-tag install and its no-web-UI caveat, MCP config uses
  an absolute path, first semantic search notes the model download.
  Contributors credited.
- CODE_OF_CONDUCT names a contact.

### Changed

- **`auto_embed: true` now guarantees that an entry *will be* embedded, not
  that it is embedded when the write returns (ADR-0035).** A write records the
  entry, makes it keyword-searchable immediately, and notes one `pending` row
  in `embed_queue`; it never imports torch and never touches the network.
  The debt is paid on paths that already have a caller willing to wait —
  `pyrite index embed` / `index sync` / `index build`, every `pyrite-server`
  startup, and `POST /api/index/sync?wait=true` — and
  `GET /api/index/embed-status` reports what is outstanding. **Semantic search
  is therefore eventually-consistent:** an entry written a moment ago may not
  be findable by meaning until a drain runs, and a semantic search against a
  KB with no embeddings now says so in `warnings` (naming `pyrite index
  embed`) instead of returning a silent empty list. No background thread is
  introduced (deliberately not copying #102's unjoined daemon thread).
  `auto_embed: false` is unchanged: nothing is enqueued and no embedding code
  is reached at all.
- **MCP reads are bounded by default, and the bound can no longer be
  defeated (ADR-0034 rules 1, 3, 4).** Two behaviour changes for clients
  passing large `body_limit`s: the per-body ceiling drops from **50,000 to
  20,000** characters (92% of measured bodies still fit in one call; the
  rest continue with `kb_read_body`), and multi-entry reads gain a
  **per-response budget of 40,000 body characters** — previously the
  ceiling was per body, so 50 entries at it was a megabyte. Bodies fill in
  request order; an entry reached after the budget is spent comes back in
  place with an empty body, `body_truncated: true` and its true
  `body_length`, never dropped and never reported `not_found`.

  All three numbers are now configuration read at server start —
  `PYRITE_BODY_CHUNK_DEFAULT` (8000), `PYRITE_BODY_CHUNK_MAX` (20000),
  `PYRITE_BODY_RESPONSE_BUDGET` (40000). An invalid value (non-integer,
  ≤ 0, or a default above the max) stops the server with a message naming
  the variable rather than silently falling back, and the MCP tool
  descriptions report the effective values instead of compiled-in ones.

- **A `fields` projection no longer skips body chunking** — the documented
  contract it replaces is retired (ADR-0034 rule 1: a parameter that
  reduces output never disables another bound). `kb_get` and
  `kb_batch_read` with `fields=[..., "body"]` and `body_limit=6000`
  returned 171,189 characters, 28× the explicit cap (#58); the same call
  now returns 12,369. A projection that keeps `body` also keeps
  `body_truncated`, `body_length`, `body_offset` and `body_chunk_size`, so
  a truncated body can still be recognised as one.

  The same hole was open on three read paths the issue did not name, and
  they are closed with it: `kb_search` returned whole bodies for both
  `include_body=true` and `fields=[..., "body"]` (it has no `body_limit`
  at all, so it is bounded at the default chunk within the response
  budget), and `kb_list_entries` and `kb_recent` returned whole bodies for
  up to 200 entries whether or not `fields` was passed.

- Three open process findings fixed: `.claude/THEME.md` is no longer tracked
  (it was gitignored but the already-committed blob kept riding every branch,
  risking add/add conflicts — #122); `scripts/verify-red.sh` now refuses
  (exit 2) when a reverted production file's top-level package resolves
  outside the worktree's interpreter, so a review worktree with a symlinked
  `.venv` can no longer report a suite number measured against the wrong
  checkout — #189; and the PR gate's `changes` classifier gained an `infra`
  output that widens the `test` job's matrix to all three interpreters when a
  PR touches test infrastructure (`conftest.py`, `pyproject.toml`,
  `.pre-commit-config.yaml`, `ci.yml`, `scripts/*`), so a change whose
  behaviour is a property of the interpreter — like #81's `@classmethod`
  fixtures — can't merge green on 3.12 and redden `dev` on 3.13 — #133.
- `web/` dependency bumps (supersedes Dependabot PRs #23-#29, one reviewable
  change): `@sveltejs/kit` 2.53.0→2.70.3 (security fixes — CSRF protection on
  non-production `NODE_ENV` builds, prototype pollution in file-input
  deletion, quadratic-backtracking DoS in `Accept` header negotiation, cookie
  size aligned to RFC 6265bis; also moves `defineEnvVars` to
  `@sveltejs/kit/env`), `@tiptap/core` 3.20.0→3.31.3 (fixes a `mergeAttributes()`
  prototype-pollution advisory and a ReDoS in Markdown attribute parsing;
  pulls `@tiptap/pm` and the prosemirror-* family along in lockstep, and drops
  now-unused transitive deps `linkify-it`/`markdown-it`/`@remirror/*`), vitest
  4.0.18→4.1.11 (with `@vitest/mocker` and the rest of the `@vitest/*`
  family), undici 7.22.0→7.29.1 and nanoid 3.3.11→3.3.19 (both transitive,
  under `jsdom` and `vite`→`postcss` respectively — no direct `package.json`
  entry), devalue 5.6.3→5.9.2 (transitive under `@sveltejs/kit`; also fixes a
  prototype-pollution advisory). `npm audit --omit=dev`: 12 vulnerabilities
  (2 low, 2 moderate, 8 high) before → 8 (4 low, 1 moderate, 3 high) after.
  No source changes required; build, 388 unit tests and `svelte-check`
  (449 files, 0 errors, the 23 pre-existing a11y warnings) all still pass.
- `web/e2e/collections.spec.ts` and `web/e2e/daily.spec.ts` (Package E of the
  Playwright determinism ticket) now assert on the seeded world instead of
  "a list or an empty state": the collection's membership is exactly the
  three seeded people, and `daily.spec.ts` only ever navigates within
  `SEEDED_DAILY_DATES` (auth is disabled in the e2e world, so `GET
  /daily/{date}` creates a note for a date that has none). Found two real
  product bugs in the process (`test.fixme`'d, not papered over): the root
  layout overwrites every route's `<title>` with the bare brand name
  (#49, pre-existing), and `Calendar.svelte`'s month-navigation buttons are
  inert wherever a `selectedDate` is set — an effect immediately snaps the
  view back (#89).
- `web/e2e/search.spec.ts` and `web/e2e/qa.spec.ts` (Package G of the
  Playwright determinism ticket) now assert on the seeded world instead of
  `.or(...)` "results or an empty state" dodges: a seeded query renders the
  seeded entry's title **as a result link** with the loading skeleton gone at
  that moment (`web/e2e/search.spec.ts:44`) — the assertion issue #9 needed to
  be closed, since the "N results" header alone can't distinguish a rendered
  list from one stuck on the skeleton. Removing the `.or()`/`if (count > 0)`
  dodges surfaced that the seeded world is not the zero-issue QA state the
  ticket assumed: `global-setup.ts` creates no links between entries (the
  same fact `graph.spec.ts` already asserts against `/api/graph`), so
  `qa_service.py`'s `orphan_entry` rule fires for every seeded entry, every
  run — `qa.spec.ts` now asserts that deterministic count instead of a
  clean-state dodge. `aria-label` added to the four unlabeled `<select>`s
  (search's KB and type filters, QA's severity filter) and `aria-pressed` to
  the search mode buttons, plus `data-testid` on the search skeleton, the
  search empty state, and the two QA stat cards — additive attributes only,
  no guard logic changed. The two `toHaveTitle` assertions are dropped
  (comment naming #49), following package F's precedent.
- The Playwright e2e suite now seeds and runs against its own KB in a private
  data directory (`web/e2e/global-setup.ts`, contract in `web/e2e/fixtures.ts`)
  with auth explicitly disabled and no server reuse, instead of whatever
  `~/.pyrite` happened to contain — which is why it had been failing
  differently on every run.
- 100 auth tests (`test_auth_endpoints`, `test_auth_service`,
  `test_github_token_storage`, `test_daily_endpoints`, `test_repo_endpoints`,
  `test_ai_quota_enforcement`) now run in CI. Each module carried a stale
  `pytest.importorskip("passlib")` although nothing imports passlib; a fresh
  install never has it, so CI had been reporting those six modules as "1
  skipped" each on every green run.
- The embedding model is loaded once per process and shared by every
  `EmbeddingService` instance (it was loaded per instance; the service is
  constructed in nine places).
- The test suite no longer loads the sentence-transformers model unless a test
  is marked `@pytest.mark.embeddings`. Every entry write in every test had been
  importing torch (~3 s) and calling the Hugging Face hub for metadata; under
  `-n auto` ten workers doing that at once thrashed the machine, and unrelated
  tests showed up at 50+ s.
- CI has one required check, `gate`, so a docs-only PR (matrix skipped) can
  merge; requiring matrix legs by name hung the first such PR.
- CI installs with `uv` (80-130 s of pip resolving per job → ~20 s). A change
  classifier skips the heavy jobs for docs/KB-only pushes and gives KB changes
  a 30 s schema check. Coverage runs in its own job, by manual dispatch only until there is a
  baseline worth enforcing.
  Pull requests test one interpreter (3.12); the push to `dev` after a merge
  runs the full Python matrix (ADR-0032 value chain). Playwright
  runs only by manual dispatch until it is deterministic.
- The test suite runs in parallel (`pytest -n auto`) at pre-push and in CI:
  ~22 min → ~3-5 min. The one xdist-unsafe test (the task-claim race) now uses
  a start barrier and a single group deadline instead of per-process timeouts,
  which also makes it a real race rather than a sequence under load.
- `social`, `zettelkasten` and `encyclopedia` relabelled as example plugins
  (README, `docs/plugins.md`, `docs/getting-started.md`, each extension's new
  `README.md`, `kb/components/*-extension.md`, `pyproject.toml`
  `description`): reference code showing how a Pyrite plugin adds entry
  types, CLI commands, MCP tools and a preset, not supported products.
  Wording only — no package name, entry point, module path, preset name,
  template name, CLI command name, MCP tool name or directory changed.
- CONTRIBUTING: how to claim an issue

### Fixed

- **The first write on a fresh install no longer blocks for over a minute
  downloading the embedding model (#13).** `KBService._auto_embed` took a
  synchronous branch whenever `self._embedding_worker` was unset — and nothing
  in production ever set it, so *every* write on *every* surface imported
  torch and fetched ~90 MB inside the request. Writes now enqueue (see
  ADR-0035 under Changed): measured on a live `pyrite-server` with an empty
  `HF_HOME` and the network blocked, `POST /api/entries` returns in
  milliseconds instead of failing a 2 s budget, and the entry is
  keyword-searchable at once.

- **Writing back a body that a bounded read had truncated silently destroyed
  the rest of the entry.** `kb_get`/`kb_batch_read` return at most the default
  chunk (8,000 characters, `PYRITE_BODY_CHUNK_DEFAULT`) of a long body plus
  `body_truncated: true`; nothing refused that body on the way back in, so an
  agent that edited what it received and saved it replaced a
  170,000-character entry with that fragment — silent, permanent, and produced
  by the safety feature itself. 21% of entries on the maintainer's index are
  long enough to be affected. Every write surface that can receive a
  body now refuses one carrying a truthy `body_truncated` marker, with
  `VALIDATION_FAILED`, `retryable: false` and a message naming `kb_read_body` /
  `body_offset` as the way to assemble the whole body first: MCP's write and
  admin tiers (`kb_create`, `kb_update`, `task_create`, `task_decompose` and
  any plugin write tool, guarded at the dispatcher), `kb_bulk_create`
  per-item, REST `POST`/`PUT`/`PATCH /api/entries` plus
  `POST /api/entries/import` per-record, and the CLI — `pyrite import`
  per-record (exiting 1, so a script cannot read "Imported N" off a run that
  dropped a truncated body), `pyrite create` and `pyrite update`. A write
  without the marker, a write carrying `body_truncated: false`, and a
  metadata-only update that carries the marker but no body are all unaffected.
  ADR-0034 rule 2; the CLI half closes #230.

  `pyrite create --body-file`/`--stdin` lifts a file's YAML frontmatter into
  the entry's fields, so a bounded read saved to a scratch file — the most
  likely way a marker gets persisted before being replayed — is refused too.
  `pyrite update --body-file` does not parse frontmatter and is unchanged: a
  marker there is body content, not a write argument.

  Importer audit: `json` and `markdown` carry the marker through to the
  caller, `yaml` and `csv` strip it through their key whitelists. Both import
  endpoints check every record regardless of format.

- **Extension entry classes silently dropped `aliases` and `_schema_version` on
  every load -> save round trip, and rewrote `importance` back to its default**
  — a `writeup` (social), `zettel`/`literature_note` (zettelkasten), or
  `article`/`talk_page` (encyclopedia) saved at `importance: 9` came back
  `importance: 5` on the next save, because each class's `from_frontmatter`
  hand-rolled its constructor call instead of routing through
  `Entry._base_kwargs`, and `extra_frontmatter` could not rescue the loss since
  all three keys are members of `_BASE_CONSUMED_KEYS`. All six classes now call
  `cls._base_kwargs(meta, body)`; the same hand-rolled-copy pattern in
  `cascade`, `journalism-investigation`, `software-kb` and
  `pyrite/models/task.py` is deleted in favour of the one shared
  implementation. A new registry-wide conformance test in
  `tests/test_frontmatter_round_trip_all_types.py` parametrizes over every
  registered entry type (core + every installed plugin) and pins the
  guarantee for future types automatically.
- **The REST `POST /entries/batch` endpoint now matches the MCP
  `kb_batch_read` contract.** A malformed spec returns a structured
  `VALIDATION_FAILED` (HTTP 400) naming `entries[i]` instead of a 500, a
  `fields` value that is not an array of strings gets the same
  `VALIDATION_FAILED` instead of a near-empty 200, and the `fields` projection
  always keeps `id` and `kb_name`, so `found` can no longer contradict
  `not_found` (#134).

- KBs removed from `config.yaml` become user-managed on the next registry
  sync, so `pyrite kb remove` no longer rejects them indefinitely. Existing
  index data and permissions are preserved; KBs still in the config remain
  protected (#19).
- **`kb_batch_read` no longer crashes on a malformed spec, and every `fields`
  projection keeps the identity pair.** A non-list `entries`, a non-object item,
  or a missing, empty or non-string `entry_id`/`kb_name` used to raise a raw
  `KeyError`, a `TypeError` or a SQL binding error that surfaced as
  `INTERNAL`/`retryable: true`; each now returns `VALIDATION_FAILED` with
  `retryable: false`, naming the offending `entries[i]`. `_project_fields` keeps
  `id` and `kb_name` in every projection (`kb_search`, `kb_get`,
  `kb_list_entries`, `kb_recent`, `kb_batch_read`), so the schema sentence is
  true of all five (#126, #137).
- **A bare YAML date in frontmatter (`created_at: 2026-01-15`) read back as
  the load time instead of the file's date.** The YAML parser produces a
  `datetime.date` for a bare date, and `parse_datetime` only handled
  `datetime`/`str`, so the value fell through to the "now" fallback. Bare
  dates are now anchored to midnight UTC; naive ISO-8601 strings and naive
  datetimes (an unquoted `created_at: 2026-01-15T09:00:00` loads as a naive
  `TimeStamp`) are anchored to UTC as well, so comparisons against `_utcnow()`
  cannot raise `TypeError`. Timestamps are indexed as strings, so an existing
  KB may hold both `2026-01-15T09:00:00` and `2026-01-15T09:00:00+00:00` for
  unchanged files until a full `pyrite index build` makes them uniform;
  ordering and date filters are unaffected ("+" sorts before digits) (#151).
- **Two worktrees running the Playwright e2e suite at once collided on the
  same four ports (8088/5173 base, 8189/5274 auth) and could end up talking
  to each other's world.** Ports and data directories are now derived per
  worktree from a stable hash of its path (`PLAYWRIGHT_E2E_PORT` /
  `PLAYWRIGHT_E2E_VITE_PORT` still override), `strictPort: true` on Vite
  defeats its silent fallback to the next free port, and a preflight in
  `global-setup.ts`/`auth-setup.ts` fails fast — naming the port and the
  owning process — if something outside this worktree already holds it.
  `scripts/new-worktree.sh` records the chosen ports in `.pyrite/e2e-ports`
  for a human running the suite by hand. Side effect worth knowing: `vite dev`
  (including plain `npm run dev`, not just the e2e suite) now also has
  `strictPort: true` — a taken 5173 is a startup error instead of silently
  moving to 5174, which is the same silent-fallback problem this fix exists
  to close, just visible outside the e2e path too.
- **Search filters were silently ignored in semantic and hybrid modes — and
  hybrid is the default.** `entry_type`, `tags`, `state`, `fips` and `status`
  were compiled only into the keyword leg's `WHERE`; the vector leg ran with
  `kb_name` alone and the two were fused, so a filtered search returned
  plausible-looking entries the filter excluded (`--type mechanism` returning
  themes; a bogus type returning a full result set instead of zero). Every
  filter is now applied on every leg in every mode: `SearchBackend.search_semantic`
  takes the keyword leg's filter set, and all backends implement it — SQLite
  escalates sqlite-vec's KNN budget so a selective filter costs no recall,
  Postgres puts the predicates in the same `WHERE` as the distance ordering.
  The backend conformance suite gained the semantic-filter cases. When a leg
  cannot honour a filter it is dropped rather than returning unfiltered rows,
  and the response carries a `warnings` array naming the filters responsible
  (`GET /api/search` and MCP `kb_search`; on stderr for the CLI) — absent, never
  null, when everything was applied, so a caller tests for the key. Whether a
  backend can filter its vector leg is a declared capability
  (`BackendCapability.FILTERED_SEMANTIC`), not a probe: an earlier draft
  inferred it from a `TypeError`, which turned any genuine bug inside the
  vector leg into a silently dropped one. The archived-entry exclusion counts
  as a filter and now holds on the vector leg too. `limit` is validated at the
  service boundary rather than failing as a `TypeError` or a SQLite error deep
  inside a leg. Two notes for operators: SQLite's KNN escalation is capped at
  sqlite-vec's hard ceiling of `k = 4096`, so on an index larger than that a
  filter selective enough to exclude the 4096 nearest neighbours under-returns
  on the vector leg (best-effort recall — the keyword leg has no such ceiling
  and carries hybrid); and the `kb_names` permission allowlist remains a Python
  post-filter (`SearchService._restrict`) rather than a backend predicate,
  unchanged by this work and correct, since it over-fetches before restricting.
  Fixes #56, #53.
- **The New Entry page's Create button could submit before the target KB was
  known.** `kbStore.activeKB` resolves asynchronously on mount; nothing
  disabled Create while it was still empty, so a fast click sent `kb: ''` and
  silently failed (a toast that dismisses in 3s, no navigation) instead of
  creating the entry. The button is now disabled until the KB has resolved,
  same as it already was while saving. Found while rewriting the e2e suite's
  entry-creation coverage against a real, seeded backend.
- **The login and registration forms no longer show the HTTP status to the
  user.** Both rendered `ApiError.message`, the developer-facing string, so a
  mistyped password read "API Error 401: Invalid username or password". They
  now render the server's own `detail`. Found by the new auth-enabled
  end-to-end project, where a real 401 is reachable.
- **The login path is covered end to end.** `web/e2e/auth.spec.ts` runs under
  its own Playwright project against a backend with auth enabled — its own
  data directory, port and dev server — so the gate redirect, the API's 401
  for an anonymous request, a real sign-in, and the redirect away from
  `/login` once signed in are all asserted. Under the auth-disabled world the
  other specs use, 8 of those 18 assertions are false, which is what the
  second world buys.

- `kb_link` now verifies that both endpoints exist before writing a link, so
  a misspelled or deleted target cannot create a dangling outlink. Missing
  source or target entries return a non-retryable `LINK_FAILED`. A caller that
  genuinely wants a forward reference passes `allow_dangling: true`, and the
  response carries `resolved` so it can tell a link that landed from one still
  waiting for its target. `pyrite link` on the CLI goes through the same
  service call and is now strict, with no flag to opt out;
  `pyrite links bulk-create` writes links through the model directly, so it is
  unaffected. The target is looked up in the index first and confirmed on
  disk, so an entry created but not yet indexed still validates. (#97)
- **Typed entries no longer drop frontmatter they do not declare.** A load ->
  save through any typed class (core or plugin) deleted unknown keys —
  `pyrite update -f status=done` stripped `milestone:` and `created:`. The
  base class now round-trips them; every one of the 48 registered types is
  tested. (#15)
- **`pyrite update` no longer rewrites frontmatter it was not asked to touch.**
  Updating one field (`--tags`, `--title`, `-b`) added `body:` (the whole body
  as a YAML string), `file_path:` (an absolute path), `importance: 5` and
  `rank: 0` to the file, and reordered and restyled every remaining key; six KB
  items were corrupted this way in one loop. The loader was injecting two model
  internals into the frontmatter dict that decides which keys are "unknown and
  must be preserved", so they were preserved into the file. A one-field update
  is now a one-line diff, keeping key order, quoting and `tags: [a, b]` flow
  style. The rule holds for every entry type, not just the two originally
  guarded by hand: 32 of the 48 registered types wrote some field at its
  default whatever the file said (`adr_number: 0` and `status:` onto an ADR,
  `maturity:` onto a zettel, `priority: medium` onto a backlog item), and the
  suppression is now applied once at the file-write boundary, so a plugin type
  gets it without declaring anything. Setting such a field to its default on
  purpose still writes it. (#46)
- **`pyrite index health` exits 1 when it reports unhealthy.** It printed
  `"status": "unhealthy"` and exited 0, so every script, CI step and agent
  gating on the exit code read a failure as success; the verdict was also
  skipped entirely on the `--format json` path everyone scripts against.
  `--no-fail` keeps the old behaviour, and new `-k/--kb` scopes every check to
  one KB so another KB's problems cannot decide this project's verdict. (#18)
- **`pyrite db backup` writes beside the index, not into the current
  directory.** The default path was a bare relative filename, so backups landed
  wherever the command was run; the repo root had accumulated 125 of them
  (58 MB), gitignored so nobody noticed. The default is now
  `<data dir>/backups/`; `--output` is unchanged. (#21)
- **Writes are validated.** `create` and `update` refuse a value the KB schema
  or a plugin validator rejects (`status=bogus`, `priority=9999`) and name the
  allowed values, on every surface; the file is not touched. Previously only
  `index health` noticed, afterwards. (#14)
- **Entry ids from any title.** Accents transliterate (`cafe-resume-naive`
  instead of `caf-r-sum-na-ve`), a title with nothing Latin in it gets a
  stable `entry-<hash>` id instead of failing with "Entry must have an ID",
  and ids are capped at 80 characters instead of an `OSError`. ASCII titles
  are unchanged. `sw new-adr` (CLI and MCP) uses the same function, so `/`
  and `:` no longer reach the filename. New entries end with one newline, so
  the end-of-file hook no longer rewrites every freshly created file. (#16, #17)
- Entry files are written atomically (temp file + `os.replace`), preserving the
  file's mode. A concurrent reader could previously see a truncated or empty
  entry while another process was saving it — two agents on one KB (claim vs
  reset, claim vs claim) hit exactly that path.
- Pre-push hooks: every non-pytest hook is pinned to the commit stage, so a
  push runs only the test suite (the file fixers had been running over the
  whole pushed range and aborted the v0.24.1 push of a CI-verified commit)

## [0.24.1] - 2026-09-17

Five months of work across about 250 commits (roughly 175 substantive, 75
KB/docs), from
2026-04-06 to 2026-09-17. Versions 0.21–0.24 were tagged without CHANGELOG
entries; this section covers everything since v0.24.0 and is the first
release note written since 0.20.0.

**Why 0.24.1 and not 0.25.0.** The roadmap defines 0.25 as "Field Hardening &
Shared-Instance Pilot," whose definition of done is *one peer, logged in,
searching the corpus read-only for two weeks with zero operator
interventions.* That has not happened: the epic stands at 7 of 17 subtasks,
with the entire web-UX workstream still open. This release is the accumulated
hardening work, not that milestone. Calling it 0.25.0 would mark a milestone
shipped whose defining goal was never attempted.

**First GitHub release.** None existed before this tag, so nothing was
pinnable and `publish.yml` had never fired.

**No PyPI wheel.** The `pyrite` name on PyPI is held by a pre-2FA account
that is locked. Install from a source checkout (README Quick Start), or
`pip install "pyrite[all] @ git+https://github.com/markramm/pyrite@v0.24.1"`.
The git install gives you the CLI, the REST API and the MCP server, **but no
web UI**: the built frontend is not packaged yet, and the server does not say
so (`installable-from-github-with-a-working-web-ui-package-the-built-frontend`).
For the UI, use a source checkout (`cd web && npm ci && npm run build`) or Docker.

**Frontend caveat.** The Playwright e2e job is currently non-blocking (see
`playwright-e2e-suite-non-deterministic-failures-likely-shared-state-auth-config-gap`),
so CI green means the backend is green. `web-search-results-never-render` is
open and describes the search page showing permanent skeletons for
anonymous/read sessions. Verify the web UI by hand before relying on it.

### Highlights

- **Error handling became a contract** — typed domain errors, a central REST
  exception handler, and a CLI-wide sweep converting every ad-hoc error site
  to a shared helper. Tracebacks no longer leak from CLI commands.
- **Fail-closed sweep** — auth tokens, plugin compatibility checks, index
  drift detection, and push failures stopped converting failure into false
  success at trust boundaries.
- **Index correctness** — read-back verification on rename, content-hash
  staleness detection, DB-registered KBs enumerated in every health loop,
  and warnings for undeclared types and missing `type:` frontmatter.
- **Plugin capability declarations** (ADR-0002 addendum) and **per-entity-type
  state machines** (ADR-0027).
- **KB-type-scoped entry-type resolution** — fixes a per-machine
  nondeterminism where the same code resolved `person` differently depending
  on site-packages enumeration order.
- **White-label branding** across site-cache, web frontend, KB export, and
  MCP prompts.
- **Three community contributions** — first outside PRs to the project.

### Added

- **Task workflow**
  - `pyrite task reset` releases stale claims back to `open`
  - `cancelled` terminal state for obsolete tasks
  - `--comment` flag records why a status transition happened
  - `--reason` / `status_reason` field for relaxed-mode transitions
  - `GET /api/tasks` and a human worklist board at `/tasks`
  - Per-entity-type `state_machine` config with `migrate-relaxed-mode` CLI (ADR-0027)
- **Search & index**
  - `--status` filter wired through CLI, service, all backends, and MCP
  - OR-relax on zero-hit keyword queries to fix brittle recall
  - Observability trace: mode, fallback reason, and latency logged per query
  - Stderr warning when the index is stale, naming the affected KBs
  - `pyrite qa coverage` curation statistics
  - `pyrite rename` for same-KB entry rename with wikilink rewrite
- **Plugins & backends**
  - `BackendCapability` enum with method-capability dispatch
  - Plugin capability declarations with dispatch-skip (ADR-0002 addendum)
  - `HookRunner` extracted as a peer service; `KBService` delegates to it
- **Branding & publication**
  - `BrandingService` with public `/config/branding` and `/branding/{file}`
  - White-label branding in web frontend, site-cache, KB export footer, MCP prompt
  - `sitemap.xml`, `robots.txt`, and complete SEO meta on entry pages
- **Quotas & AI**
  - Per-user LLM usage tracking (`llm_usage` table, REST endpoints)
  - `QuotaService.check_llm_quota`, wired into AI endpoints with tier resolution
  - Anthropic prompt-caching surface on `LLMService`
  - Configurable, visible embedding body truncation
- **CI**
  - Frontend and Playwright e2e jobs
  - pgvector-enabled postgres service exercising both backends
  - mypy strict-ratchet scaffold for `pyrite/storage/`
- **Web**
  - Entry comments panel and submit-for-review flow
  - `fips` and `state` as promoted entry columns with search filters

### Fixed

- **MCP tools that failed on every call** (found by a new smoke test that
  dispatches every registered tool)
  - `task_subtree`, `task_ancestors`, `task_blocked_by`, `task_critical_path`
    (`AttributeError`; also resolve the task's KB when `kb_name` is omitted)
  - `kb_manage` `discover`; zettelkasten's zettel listing (invalid FTS5 `*`
    query); journalism-investigation cross-KB search on hyphenated queries and
    investigation setup against a missing KB (raw `IntegrityError`)
- **Creating an entry whose id already exists silently replaced the existing
  entry** and reported "Created" — on every surface (CLI, REST, MCP, importers).
  Ids come from titles, so two entries with the same title destroyed the first.
  Create now refuses; use update to replace.
- MCP: refused requests (validation, not found, read-only) were reported as
  `INTERNAL, retryable: true`, inviting agents to retry calls that cannot succeed.
  They now return stable codes (`VALIDATION_FAILED`, `NOT_FOUND`, `READ_ONLY`, …)
  with `retryable: false`.
- `pyrite.__version__` reported `0.12.0`; it now reads the packaged version
- `LICENSE` was missing a clause of the MIT text and named no copyright holder
  (GitHub showed the license as "Other")
- `CONTRIBUTING.md` told contributors to install `.[dev]`, which cannot run the
  test suite; it now says `.[all]` plus the extensions
- **Index & storage**
  - New entries of plugin types (e.g. `backlog_item`) were filed under the
    parent core type's directory (`notes/`) when `kb.yaml` declared the type
    without a `subdirectory`; the owning plugin's preset default now applies
  - `index sync` silently skipping modified files
  - Frontmatter delimiter matching inside quoted values; wikilink extractor
    counting code fences and path-like targets as broken links
  - Read-back index verification on rename, hard error on drift
  - Content-hash staleness detection in `check_health()`
  - DB-registered (`kb add`) KBs now indexed by `sync`/`build` and enumerated
    in staleness/health/stats/edge-type loops (#2)
  - Metadata clobbering on partial update; metadata threaded through REST
  - Deliberate subdirectory preserved on update instead of relocating to the
    type default
  - `EventEntry` serializes `actors`, not `participants`
  - `TaskEntry` preserves unknown top-level frontmatter keys across
    load → save. `task claim` / `task update -s` were silently stripping
    conventions like `parked_awaiting:`, turning parked monitors into
    apparently stalled work. `NoteEntry` and `CollectionEntry` still drop
    them (`core-types-silently-drop-unknown-frontmatter-keys`, open)
- **Fail-closed / error handling**
  - Auth fails closed on undecryptable GitHub tokens and API keys
  - Plugin KB-type compatibility check fails closed
  - Real push failures no longer masked as "No remote configured"
  - Invalid-status drift detector and references-extraction fallback now warn
    instead of degrading silently
  - FTS5 syntax errors classified as `QUERY_SYNTAX`, not `INTERNAL`
  - FTS5 terms quoted in `links suggest`/`discover` (fixed `links orphans` crash)
  - Malformed frontmatter, illegal task transitions, and undeclared types
    surface as clean errors rather than tracebacks
  - Malformed files collected as a sync summary instead of traceback spew
- **Type resolution**
  - Entry-type resolution scoped by KB type; most-derived-class tiebreak.
    Previously the first plugin subclass in discovery order won, so `person`
    resolved to `actor` or `user_profile` depending on the host's
    site-packages enumeration (`plugin-type-resolution-scoping` item 1)
- **Auth & web**
  - OAuth CSRF state moved from an in-memory dict to the DB (survives restart)
  - KB store loads after auth init, preventing 401s on protected instances
  - Entry page scroll broken by nested overflow containers
  - Search crash on entries sharing an ID across KBs
  - Checkbox field widget on the new-entry form
  - Daily-notes navigation no longer performs a write for read-tier users
- **Concurrency & tests**
  - `IndexWorker` thread-leak flake root-caused
  - `GitService` subprocess env isolated from a parent git process
  - N-process concurrency race test for the task-claim CAS

### Changed

- CLI error sites converted to a shared `cli_error` helper across all command
  modules; `task status` renamed to `task get`
- `pyrite mcp --tier` flag implemented (previously documented but absent)
- Static renderer path deprecated in favor of the site cache
- `--include-body` contract locked; stdout stays pure JSON in `-f json` mode
- Backlog status vocabulary normalized and enforced at index time

### Security

**If you run `pyrite-server` with a GitHub token configured, or expose it to
more than one user, upgrade.**

- **GitHub token disclosure.** Repo URLs were matched against `github.com` as a
  substring, so `https://evil.example/github.com/a/b` was treated as a GitHub
  repo and the server's token was sent to that host. Reachable by a write-tier
  caller through `POST /repos/subscribe`. The host is now parsed and compared
  for equality; userinfo and non-https schemes are refused; owner and repo
  names are validated.
- **Git argument injection.** `clone` and `git add` passed caller-supplied
  values without `--`, so a value starting with `-` was read as a git option
  (`--upload-pack=<cmd>` executes). Both now use `--` and refuse option-shaped
  input.
- **Mutating routes reachable at read tier.** `POST /kbs/{kb}/export` (clone and
  push a whole KB to a caller-chosen URL), `POST /collections` and
  `POST /ai/test` had no tier guard; all three now require write tier. A new
  test calls every mutating `/api` route with a read-tier key and requires 403,
  so an unguarded route fails CI.
- **Stored XSS in the web UI.** Rendered markdown went into the page
  unsanitized on the entry page and in daily notes, and an entry title could
  break out of the JSON-LD `<script>` block. Rendered HTML now passes through
  DOMPurify; `<` is escaped in JSON-LD.
- **Path traversal through entry ids.** An entry id becomes a filename, and the
  REST import endpoint took `id` from the uploaded file unchecked, so a write-tier
  caller could write a `.md` file outside the KB directory (`../../x`);
  `pyrite rename` had the same hole locally. The repository now refuses ids that
  are not plain filenames and refuses any path that resolves outside the KB root.
- Web clipper SSRF defense: private, loopback, and link-local IPs blocked

### Community contributions

First outside PRs to the project, all from **Ruslan Terekhov (@AsyncLegs)**:

- **#3** — MCP SSE endpoint: pinned `mcp>=1.0.0,<2.0.0` (a fresh install was
  resolving 2.2.0, two majors past the 1.x `Server` API `build_sdk_server()`
  uses) and fixed a doubled `/mcp/mcp/messages/` path where the SSE transport
  was constructed with an endpoint that already included its mount prefix
- **#4** — KB created via `POST /api/kbs` was invisible to entry creation
  until restart: `add_kb()` wrote to the DB without updating the in-process
  `_db_kb_cache`
- **#5** — `EmbeddingService.prewarm()` was never called despite
  `PYRITE_PREWARM_EMBEDDINGS=true`; `/health`'s `embeddings.ready` stayed
  permanently false

### Known gaps at this release

- The former `[Unreleased]` section is now retitled `[0.21.0 – 0.24.0]`: its
  contents all date to 2026-03-23 → 2026-03-26 and shipped in those tags,
  which were cut without CHANGELOG entries. It is not split per-tag, because
  the four versions were cut within days of each other and the log does not
  cleanly attribute features to individual tags.
- `web/package.json` is stranded at `0.20.0`, four minors behind the Python
  package. Whether the frontend versions independently is an open question
  under ADR-0031 (`pyrite-core-ui` as an addressable package), so it was not
  bumped blindly here.
- Stale PyPI claims remain in `kb/designs/launch-staging.md:32` (ticked
  `[x] pip install pyrite works`), `launch-channels.md`, and
  `bhag-self-configuring-knowledge-infrastructure.md`. They describe a path
  that the locked account makes unreachable.

## [0.21.0 – 0.24.0] - 2026-03-23 → 2026-04-06

Reconciled 2026-09-17. This content was written by `ab0707c` ("Document all
post-0.20.0 work in CHANGELOG", 2026-03-26) and sat under `[Unreleased]`
because 0.21.0 through 0.24.0 were tagged without CHANGELOG entries. Every
item below dates to 2026-03-23 → 2026-03-26 and therefore shipped in those
tags; it was never pending work.

Not split per-tag: the four versions were cut within days of each other and
the commit log does not cleanly attribute these features to individual tags.

**Note on the `/site/` cache:** this section records *building* it. The
0.24.1 cycle *deprecated* the static renderer path in favour of custom Hugo
sites (`12d5660`, `3d1d1e1`, 2026-04-23). Both are accurate; they are
different events five months apart.

### Added

- **Static Site Rendering (`/site/`)**
  - Python-served static HTML cache for SEO-friendly KB pages (replaces earlier Node SSR approach)
  - Sitemap.xml generation from cached pages with per-entry lastmod dates
  - robots.txt with crawler directives
  - JSON-LD structured data, Open Graph meta tags, canonical URLs on every page
  - Custom homepage support via `_homepage` KB entries with designed template rendering
  - Progressive JS enhancements: live search widget, auto-generated TOC, heading anchors, back-to-top
  - Editorial dark theme with Source Serif 4 body + DM Sans headings
  - `/site/search` page with live API-backed hybrid search and URL state sync
  - Cache invalidation per-entry and per-KB, auto-render on index sync

- **Web UI Feature Parity (Phase 4-5)**
  - KB orientation page with type breakdown, recent changes, and tag cloud
  - Advanced search filters: date range, tag filter, saved searches with localStorage
  - Daily notes calendar widget
  - User management: list users, role editing, per-KB permission grants/revokes
  - Index management: sync, rebuild, health check, embedding status in settings
  - Entry creation with full metadata fields (type, tags, date, importance, status)
  - Graph centrality sizing (betweenness centrality from API)
  - Review & Publish workflow: pending changes view with entry-level diffs and commit dialog
  - KB landing page at `/` with directory of knowledge bases
  - Dashboard moved to `/overview`

- **Search Improvements**
  - `group_by_kb` and `limit_per_kb` query params for cross-KB result diversity
  - Prevents large-KB dominance by returning top N results per KB with round-robin interleaving

- **Multi-Site Deployment**
  - Shared Docker network (`pyrite-shared`) for multiple Pyrite instances on one VPS
  - Caddy routing for multiple domains (demo.pyrite.wiki + capturecascade.org)
  - Independent container lifecycle per site

- **Export System**
  - NotebookLM renderer with source bundling and manifest generation
  - Quartz static site renderer for KB publishing
  - CLI `export` command group with collection and site subcommands

### Fixed

- **Security**
  - Fix 6 XSS vulnerabilities in site cache (title escaping, search widget, markdown links, ChatSidebar, search highlight)
  - Fix YAML frontmatter injection in export service (string interpolation → proper quoting)
  - Fix path traversal via entry IDs used as filenames (new `sanitize_filename()` utility)
  - Block javascript:/data:/vbscript: URLs in markdown link rendering
  - Add single-quote escaping to HTML `_esc()` function
  - Set `no-cache` on SPA index.html to prevent stale chunk hash errors after deploy

- **Bugs**
  - Fix graph KB filter SQL precedence: `WHERE (A OR B) AND C` not `WHERE A OR (B AND C)`
  - Fix Sidebar.svelte `$derived` value called as function (`{userInitials()}` → `{userInitials}`)
  - Fix QuickSwitcher full page reload (window.location.href → goto())
  - Fix anonymous access when auth not configured (anonymous_tier None handling)
  - Fix editor blank content when switching to edit mode
  - Fix layout clipping issues (flex-col, min-h-0, overflow)
  - Fix graph page zero-height container

- **Performance**
  - Site cache render_all() runs in background thread (asyncio.to_thread) instead of blocking event loop
  - Reduce N+1 queries in site cache: eliminate redundant list_entries and get_entry calls

### Changed

- Decouple `/site` and `/viewer` routes from SPA dist (work without SvelteKit build)
- Update README: MCP tools 14/6/4 → 23/11/8, extension points 15 → 19, tests 1468 → ~2500, ADRs 16 → 22
- Replace `task` with `journalism-investigation` in extensions table

## [0.20.0] - 2026-03-23

First public beta release. This release consolidates 8 milestones of development (0.10–0.18) into a single distributable package with comprehensive documentation, deployment options, and a hardened web UI.

### Highlights

- **GitHub OAuth & per-KB permissions** — multi-user access control with read/write/admin tiers
- **Docker & one-click deploy** — Dockerfile, Docker Compose, Railway, Render, and Fly.io deploy buttons
- **Web UI hardening** — 14 UX fixes, accessibility audit, Playwright E2E tests, mobile responsive
- **Agent DX overhaul** — 8 MCP tool improvements, structured error responses, batch operations
- **Architecture refactors** — KBService decomposed into 4 focused services, schema module split into 6 submodules
- **Two domain plugins** — software-kb and journalism-investigation prove the platform is general-purpose
- **Edge entities** — typed relationships as first-class entities with endpoint schemas
- **Export system** — NotebookLM and Quartz static site renderers

### Added

- **Authentication & Access Control**
  - GitHub OAuth sign-in (`oauth-providers` Phase 1)
  - Per-KB read/write/admin permissions with ephemeral KB sandboxes
  - MCP per-client per-tier rate limiting

- **Deployment**
  - Multi-stage Dockerfile and Docker Compose configuration
  - One-click deploy buttons for Railway, Render, and Fly.io
  - Self-hosted deployment scripts with Caddy reverse proxy
  - Demo site deployment tooling

- **Web UI**
  - Logout button, version history fix, type color consolidation
  - Browser tab page titles, loading state standardization
  - Accessibility fixes (aria-labels, keyboard navigation, screen reader support)
  - Mobile responsive viewport fixes
  - Collection view persistence, first-run onboarding experience
  - Starred entries restoration, dead code cleanup
  - Alpha banner with feedback button and error reporting links
  - Comprehensive Playwright E2E test suite (search, collections, QA, settings, daily, entry CRUD, auth)

- **Agent Developer Experience (MCP + CLI)**
  - `kb_batch_read` — multi-entry retrieval in one call
  - `kb_list_entries` — lightweight KB index browsing
  - `kb_recent` — orientation queries for what changed recently
  - Search `fields` parameter for token-efficient results across CLI, MCP, and REST
  - Smart field routing: top-level vs metadata field mapping clarified
  - Structured JSON error responses with `suggestion` field across all surfaces
  - MCP body chunking with auto-truncation and `kb_read_body` for large entries

- **Architecture**
  - `SearchBackend` protocol — 13-method structural protocol for pluggable storage
  - `SQLiteBackend` — wraps PyriteDB + FTS5 + sqlite-vec (default)
  - `PostgresBackend` — tsvector FTS + pgvector embeddings for server deployments
  - KBService decomposed into `GraphService`, `EphemeralKBService`, `QuotaService`, `ExportService`
  - Schema module split into 6 focused submodules (`enums`, `validators`, `provenance`, `field_schema`, `kb_schema`, `core_types`)
  - `DocumentManager` for write-path coordination
  - Entry protocol mixins for composable field patterns (ADR-0017)
  - Edge entities — typed relationships as first-class entries with endpoint schemas (ADR-0022)
  - Dynamic subdirectory paths with template variables (`{status}`, `{type}`)

- **Export System**
  - `pyrite export collection` — export entries for NotebookLM with bundling and source redaction
  - `pyrite export site` — export KB as Quartz static site for GitHub Pages
  - Quartz renderer with wikilink normalization, frontmatter mapping, project scaffolding

- **KB Quality & Lifecycle**
  - `pyrite schema validate` — frontmatter validation with ID collision detection
  - `pyrite ci` — CI/CD schema and link validation command
  - `pyrite qa fix` — auto-fix safe structural issues
  - `pyrite qa gaps` — structural coverage analysis
  - `pyrite links check` — cross-KB broken link validation
  - `pyrite links suggest` — FTS5-based link suggestions
  - `pyrite links bulk-create` — batch link creation
  - `pyrite db backup` / `pyrite db restore` — database backup and restore
  - `pyrite kb compact` — detect archival candidates with type-aware staleness
  - Entry `lifecycle` field with archive-aware search filtering
  - Intent layer: guidelines, goals, rubrics, deterministic and LLM-assisted evaluation
  - Named rubric checkers with explicit binding and CLI discoverability
  - Source URL liveness checking for QA

- **Agent Workflow (Kanban for Agent Teams)**
  - Milestone entry type with board configuration (`board.yaml`)
  - Review workflow with DoR/DoD quality gates
  - `sw_pull_next`, `sw_claim`, `sw_submit`, `sw_review`, `sw_log` MCP tools
  - `sw_context_for_item` for pulling work context
  - Work session logging with `WorkLogEntry`

- **Plugins**
  - `software-kb` plugin: ADRs, components, backlog items, standards, runbooks, kanban workflow
  - `journalism-investigation` plugin: persons, organizations, events, claims, evidence, sources with reliability tiers, ownership chains, money flow tracking, FtM interop, cross-KB entity correlation
  - `cascade` plugin: timeline events, actors, capture lanes, static JSON export for viewer consumption
  - Plugin preset registration for `pyrite init --template`
  - Init templates: `research`, `software`, `zettelkasten`, `intellectual-biography`, `movement`, `empty`

- **Documentation**
  - Getting Started tutorial
  - Plugin writing tutorial
  - OpenAI / Codex MCP integration guide
  - Gemini CLI / Antigravity MCP integration guide
  - Awesome plugins directory page

- **Infrastructure**
  - Async/queue-based index rebuild with background thread worker
  - Embedding service pre-warming to reduce cold-start latency
  - Import cycle detection guard
  - Plugin discovery strict mode (surfaces load failures during development)
  - Plugin hook atomicity (transactional wrapping for before_save hooks)
  - Bulk import CLI with `--body-file` and `--stdin` support

### Changed
- Default CLI output format changed to JSON for agent-friendly consumption
- Priority field changed from Integer to String across storage and protocols
- API module-level singletons replaced with `app.state` for test isolation
- Plugin registry deduplication on reload
- Factory pattern refactored to open/closed principle
- Incremental link sync (diff-based instead of delete-all/insert-all)
- LanceDB backend evaluated and rejected (49-66x slower indexing — see ADR-0016)

### Fixed
- Entry ID collisions across types (explicit `id` fields added)
- MCP `kb_create` placing entries at KB root instead of type directory
- MCP `kb_update` returning PosixPath serialization errors
- `sw adrs` reading date from metadata instead of DB column
- `sw_*` MCP tools reading status from metadata JSON instead of DB column
- Template filename filter dropping legitimate KB entries
- Duplicate tags and duplicate entry IDs during index sync
- Test suite clobbering `~/.pyrite/config.yaml`
- Collection type safety and endpoint hardening
- `str(None)` safety across enum validation

## [0.12.0] - 2026-03-01

### Added
- **PyPI publishing** — `pip install pyrite` and `pip install pyrite-mcp` now work
- **GitHub Actions publish workflow** — automated PyPI release on GitHub Release creation
- **MANIFEST.in** — controls sdist contents, excludes tests/extensions/web/kb
- **Schema Migration System** (`storage/migrations.py`)
  - Version tracking via `schema_version` table
  - Forward and rollback migration support
  - Auto-migration on database initialization
- **Service Layer** (`services/`)
  - `KBService` for KB operations (CRUD, indexing)
  - `SearchService` for search with FTS5 query sanitization
- **Pre-commit Hooks** (`.pre-commit-config.yaml`)
  - Ruff linting and formatting
  - Basic file checks (trailing whitespace, YAML validation)
  - Pytest quick check on commit
- **GitHub Actions CI** (`.github/workflows/ci.yml`)
  - Python 3.11/3.12/3.13 matrix testing
  - Ruff lint + format, mypy type checking
  - Separate job for full test suite with optional deps
- **Open Source Governance**
  - `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1)
  - `SECURITY.md` (vulnerability reporting policy)
  - GitHub issue templates and PR template
- **SvelteKit Web UI** (`web/`)
  - Entry browser, search, graph visualization
  - Entry editor with live markdown preview
- **Documentation**
  - `CONTRIBUTING.md` with development setup and PR workflow
  - `CHANGELOG.md`, `UPSTREAM_CHANGES.md`

### Changed
- Version bumped from 0.3.0 to 0.12.0
- Python 3.13 classifier added
- Package find excludes `pyrite-mcp/` directory
- Fixed FTS5 query sanitization for hyphenated terms
- Fixed deprecation warnings (`datetime.utcnow()` → `datetime.now(timezone.utc)`)
- Fixed sqlite3 date/datetime adapter warnings for Python 3.12+

### Removed
- Legacy `mcp_server.py` and `setup_mcp.py` root scripts
- Legacy test files importing old `zettelkasten_assistant` package
- Stale `zettelkasten_assistant` references from docs and pyproject.toml

## [0.2.0] - 2025-02-21

### Added
- **Web UI** (`ui/`)
  - Streamlit-based interface with search, timeline, actors pages
  - Entry detail view with links and sources
  - Cached data layer for performance

- **REST API** (`server/api.py`)
  - FastAPI server with OpenAPI documentation
  - Full CRUD endpoints for entries
  - Search, timeline, tags, actors endpoints
  - CORS support for web frontends

- **Agent-Optimized CLIs**
  - `crk-read`: Read-only CLI for AI agents
  - `crk`: Full-access CLI for researchers
  - JSON output format with structured errors
  - Semantic exit codes

- **Claude Code Integration**
  - `.claude/skills/kb/skill.md` for Claude Code discoverability
  - MCP server for Model Context Protocol

### Changed
- Entry points consolidated: `crk`, `crk-read`, `crk-server`, `crk-ui`

## [0.1.0] - 2025-01-15

### Added
- **Multi-KB Architecture**
  - Support for multiple knowledge bases with different types
  - Events KB for timeline entries
  - Research KB for actors, organizations, themes

- **SQLite FTS5 Storage**
  - Full-text search with BM25 ranking
  - Tag and actor indexing
  - Link/relationship storage

- **Entry Models**
  - `EventEntry` for timeline events
  - `ResearchEntry` for research documents
  - YAML frontmatter parsing

- **GitHub OAuth**
  - Private repository access for collaborative research

- **Typer CLI**
  - Rich command-line interface (`pyrite`)

## [0.0.1] - 2024-12-01

### Added
- Initial fork from joshylchen/zettelkasten
- Basic project structure
