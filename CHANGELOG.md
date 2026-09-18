# Changelog

All notable changes to Pyrite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Target: 0.24.2 "Operational" — see `kb/roadmap.md`.

### Security

- **Private KBs were readable by any logged-in user, and by anonymous
  visitors on an auth-enabled instance.** Per-KB roles (`default_role: none`,
  explicit grants) were enforced on write routes only; every read route —
  entry by id, list, search, batch read, graph, export, KB info/schema/orient —
  returned private content, and search and the KB list disclosed it. Read
  routes now require read on the named KB (404, so a private KB's existence is
  not disclosed either) and cross-KB routes are filtered to the KBs the caller
  may read, in SQL for list, count and keyword search. Operator API keys are
  unaffected (they are the operator's credential). MCP is operator-level and
  unchanged.

### Added

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

### Process

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

### Documentation

- `docs/configuration.md`: `config.yaml` and every `PYRITE_*` environment
  variable, in one place (there was none).
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

### Fixed

- **Typed entries no longer drop frontmatter they do not declare.** A load ->
  save through any typed class (core or plugin) deleted unknown keys —
  `pyrite update -f status=done` stripped `milestone:` and `created:`. The
  base class now round-trips them; every one of the 48 registered types is
  tested. (#15)
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
